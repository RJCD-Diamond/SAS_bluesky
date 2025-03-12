#!/dls_sw/apps/python/miniforge/4.10.0-0/envs/python3.11/bin/python


"""

Python dataclasses and GUI as a replacement for NCDDetectors

"""

import numpy as np
import os
import yaml
import matplotlib.pyplot as plt

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd

from bluesky.run_engine import RunEngine

from dodal.beamlines import module_name_for_beamline
from dodal.common.beamlines.beamline_utils import set_beamline as set_utils_beamline
from dodal.log import set_beamline as set_log_beamline
from dodal.utils import BeamlinePrefix, get_beamline_name
# from dodal.common.maths import in_micros
from ophyd_async.core import DetectorTrigger, TriggerInfo, wait_for_value, in_micros
from ophyd_async.fastcs.panda import (
	HDFPanda,
	SeqTable,
	SeqTrigger,
	SeqBlock, 
	TimeUnits
)

from dodal.beamlines.i22 import panda1

import bluesky.plan_stubs as bps

from ProfileGroups import Profile, Group, PandaTriggerConfig
from ncdcore import ncdcore


from ncd_panda import *

__version__ = '0.1'
__author__ = 'Richard Dixey'

############################################################################################


BL = get_beamline_name("i22")

BL_Prefix = BeamlinePrefix(BL)
print(get_beamline_name(BL))

set_log_beamline(BL)
set_utils_beamline(BL)

# print(module_name_for_beamline(BL))

# _save_panda(BL, "panda1", "/scratch/panda_test.txt")


 ##################################################################33


class PandaIO():

	def __init__(self, yaml_config):

		with open(yaml_config, 'rb') as file:
			print("Using config:",yaml_config)

			if yaml_config.endswith('.yaml') or yaml_config.endswith('.yml'):
				try:
					self.wiring_config = yaml.full_load(file)
				except TypeError:
					print("Must be a yaml file")

		self.TTLIN = self.wiring_config["TTLIN"]
		self.LVDSIN = self.wiring_config["LVDSIN"]
		self.TTLOUT = self.wiring_config["TTLOUT"]
		self.LVDSOUT = self.wiring_config["LVDSOUT"]
		self.PulseBlocks = self.wiring_config["PulseBlocks"]

##################################################################

############################################################################################

class EditableTableview(ttk.Treeview):
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.bind("<Double-1>", lambda event: self.onDoubleClick(event))

	def onDoubleClick(self, event):
		''' Executed, when a row is double-clicked. Opens 
		read-only EntryPopup above the item's column, so it is possible
		to select text '''

		# close previous popups
		try:  # in case there was no previous popup
			self.entryPopup.destroy()
		except AttributeError:
			pass

		# what row and column was clicked on
		rowid = self.identify_row(event.y)
		column = self.identify_column(event.x)

		# get column position info
		x,y,width,height = self.bbox(rowid, column)

		# y-axis offset
		pady = height // 2
		
		text = self.item(rowid, 'values')[int(column[1:])-1]

		# handle exception when header is double click
		if not rowid:
			return

		elif column == "#1": #row 1 is the group name and should just be group-n and increments for each new one
			return

		elif column in ["#4","#6"]: #these groups create a drop down menu

			# place dropdown popup properly
			options = list(TimeUnits.__dict__["_member_names_"])
			options = [f.lower() for f in options]
			
			self.dropdownPopup = DropdownPopup(self, rowid, int(column[1:])-1, text, options)
			self.dropdownPopup.place(x=x, y=y+pady, width=width, height=height, anchor='w')

			return

		elif column in ["#7","#8"]: #these groups create a drop down menu

			# place dropdown popup properly
			options = ["True", "False"]
			self.dropdownPopup = DropdownPopup(self, rowid, int(column[1:])-1, text, options)
			self.dropdownPopup.place(x=x, y=y+pady, width=width, height=height, anchor='w')


			return

		elif column in ["#9", "#10"]:

			RadioPopUp = RadioButtonPopup(self, x=x,y=y+pady)

		else:

			# place Entry popup properly
			self.entryPopup = EntryPopup(self, rowid, int(column[1:])-1, text, entrytype=int)
			self.entryPopup.place(x=x, y=y+pady, width=width, height=height, anchor='w')

			return


class DropdownPopup(ttk.OptionMenu):
	def __init__(self, parent, rowid, column, text, options, **kw):
		ttk.Style().configure('pad.TEntry', padding='1 1 1 1')

		self.option_var = tk.StringVar()
		self.tv = parent
		self.rowid = rowid
		self.column = column

		super().__init__(parent, self.option_var , text, *options) 

		self.focus_force()
		self.select_all()
		self.bind("<Return>", self.on_return)
		self.bind("<Control-a>", self.select_all)
		self.bind("<Escape>", lambda *ignore: self.destroy())
	
	def select_all(self, *ignore):
		''' Set selection on the whole text '''

		# returns 'break' to interrupt default key-bindings
		return 'break'


	def on_return(self, event):
		rowid = self.tv.focus()
		vals = self.tv.item(rowid, 'values')
		vals = list(vals)

		selection = ncdcore.str2bool(self.option_var.get())

		if selection != None:
			vals[self.column] = selection
		else:
			selection = self.option_var.get()
			vals[self.column] = self.option_var.get()
		
		self.selection = selection

		self.tv.item(rowid, values=vals)
		self.destroy()



class RadioButtonPopup():
	def __init__(self, parent, x,y, **kw):

		self.parent = parent

		print(self.parent.BeamlinePandaIO.TTLOUT.keys())
		
		root = tk.Tk()
		var = tk.IntVar()
		R1 = tk.Radiobutton(root, text="Option 1", variable=var, value=1, command=self.sel).grid(column = 0, row = 0, padx = 5,pady = 5,columnspan=1)
		R2 = tk.Radiobutton(root, text="Option 2", variable=var, value=2, command=self.sel).grid(column = 0, row = 1, padx = 5,pady = 5,columnspan=1)
		R3 = tk.Radiobutton(root, text="Option 3", variable=var, value=3, command=self.sel).grid(column = 0, row = 2, padx = 5,pady = 5,columnspan=1)
		label = tk.Label(root)
		label.pack()

		w = 300 # width for the Tk root
		h = 300 # height for the Tk root

		# get screen width and height
		ws = root.winfo_screenwidth() # width of the screen
		hs = root.winfo_screenheight() # height of the screen

		# calculate x and y coordinates for the Tk root window
		x = (ws/2) - (w/2) + x/2
		y = (hs/2) - (h/2) + y/2

		# set the dimensions of the screen 
		# and where it is placed
		root.geometry('%dx%d+%d+%d' % (w, h, x, y))
		root.mainloop()

	def sel(self):
		selection = "You selected the option " + str(var.get())
		label.config(text = selection)



class EntryPopup(ttk.Entry):
	def __init__(self, parent, iid, column, text, entrytype=int, **kw):
		ttk.Style().configure('pad.TEntry', padding='1 1 1 1')
		super().__init__(parent, style='pad.TEntry', **kw)
		self.tv = parent
		self.iid = iid
		self.column = column
		self.entrytype = entrytype
		self.insert(0, text) 
		# self['state'] = 'readonly'
		# self['readonlybackground'] = 'white'
		# self['selectbackground'] = '#1BA1E2'
		self['exportselection'] = False

		self.focus_force()
		self.select_all()
		self.bind("<Return>", self.on_return)
		self.bind("<Control-a>", self.select_all)
		self.bind("<Escape>", lambda *ignore: self.destroy())


	def on_return(self, event):
		rowid = self.tv.focus()
		vals = self.tv.item(rowid, 'values')
		vals = list(vals)

		if self.entrytype == int:
			selection = round(float(self.get()))
		elif self.entrytype == float:
			selection = float(self.get())
		else:
			selection = self.get()
			
		vals[self.column] = selection

		self.selection = selection

		self.tv.item(rowid, values=vals)
		self.destroy()


	def select_all(self, *ignore):
		''' Set selection on the whole text '''
		self.selection_range(0, 'end')

		# returns 'break' to interrupt default key-bindings
		return 'break'

class ProfileTab(ttk.Frame):

	def get_start_value(self):
		
		return self.clicked_start_trigger.get()

	def get_n_cycles_value(self):
				
		return int(self.n_cycles_entry_value.get())

	def get_inhibit_value(self):

		return bool(self.external_inhibit.get())

	def create_in_out_trigger(self):

		ins, outs = [], []

		for f in self.start_label_list:
			if "\u2191" in f:
				ins.append(f)
			elif "\u2193" in f:
				outs.append(f)

		return ins, outs


	def delete_last_groups_button_action(self):


		row_int = len(self.profile.groups)-1
		self.profile.delete_group(id=row_int)
		self.build_profile_tree()
		self.generate_info_boxes()


	def delete_group_button_action(self):

		rows = self.profile_config_tree.selection()

		if (len(rows) == 0):
			tk.messagebox.showinfo("Info","Select a group to delete")

		for row in rows[::-1]:

			row_str = "0X"+(row.replace("I",''))
			row_int = (int(row_str,16))-1
			self.profile.delete_group(id=row_int)
		
			self.build_profile_tree()
			self.generate_info_boxes()

	def insert_group_button_action(self):
		
		try:
			row = self.profile_config_tree.selection()[0]
		except:
			tk.messagebox.showinfo("Info","A row must be selected to insert it before")

			return

		row_str = "0X"+(row.replace("I",''))
		row_int = (int(row_str,16))-1
		self.profile.insert_group(id=row_int, Group=self.default_group)
		self.build_profile_tree()
		self.generate_info_boxes()


	def append_group_button_action(self):

		# row = self.profile_config_tree.selection()[0]
		# row_int = (int(row.replace("I",'')))-1
		self.profile.append_group(Group=self.default_group)
		self.build_profile_tree()
		self.generate_info_boxes()



	def build_profile_tree(self):

		try:
			del self.profile_config_tree
		except:
			pass
		
		table_row = 5

		### add tree view ############################################
		self.profile_config_tree = EditableTableview(self, columns=self.Columns, show="headings")

		widths = [100,100,150,150,150,150,150,150,150,150]

		#add the columns headers
		for i, col in enumerate(self.Columns):
			self.profile_config_tree.heading(i, text=col)
			self.profile_config_tree.column(i, minwidth=widths[i], width=widths[i], stretch=True, anchor="w")

		# Insert sample data into the Treeview
		for i in range(len(self.profile.groups)):

			group_dict = (self.profile.groups[i].__dict__)
			group_list = list(group_dict.values())[0:len(self.Columns)]

			self.profile_config_tree.insert("", "end", values=group_list)
		self.profile_config_tree.grid(column = 0, row = table_row,padx = 5,pady = 5,columnspan=len(self.Columns),rowspan=5)
		# self.profile_config_tree.bind("<Double-1>", lambda event: self.onDoubleClick(event))

		verscrlbar = ttk.Scrollbar(self, 
                           orient ="vertical", 
                           command = self.profile_config_tree.yview)
 
		# Calling pack method w.r.to vertical 
		# scrollbar
		verscrlbar.grid(column = 10, row = table_row,padx = 0,pady = 0,columnspan=1,rowspan=5, sticky='ns')
		
		# Configuring treeview
		self.profile_config_tree.configure(yscrollcommand = verscrlbar.set)

		############################################################


	def generate_info_boxes(self):
		try:
			self.total_frames_label.config(text="")
			self.total_time_label.config(text="")
		except:
			pass
			

		#### total frames
		self.total_frames_label = tk.Label(self, text=f"Total Frames: {self.profile.total_frames}")
		self.total_frames_label.grid(column = 8, row = 1, padx = 5,pady = 5 ,sticky="e" )
		### total time
		self.total_time_label = tk.Label(self, text=f"Total time: {np.amax(self.profile.duration):.3f} s")
		self.total_time_label.grid(column = 8, row = 2, padx = 5,pady = 5 ,sticky="e" )

	
	def edit_config_for_profile(self):

		for group_id, group_rowid in enumerate(self.profile_config_tree.get_children()):
			group_list = (self.profile_config_tree.item(group_rowid)["values"])
			group_properties = (Group.__dict__["__match_args__"])

			for n_col,(prop,value) in enumerate(zip(group_properties,group_list)):

				if n_col in [0,1,2,4]:
					value = int(value)
				elif n_col in [3,5]:
					value = str(value)
				elif n_col in [6,7]:
					value = ncdcore.str2bool(value)
				elif n_col in [8,9]:
					pulses = (value.replace(" ",""))
					pulses = [int(f) for f in list(pulses)]
					value = pulses

				setattr(self.profile.groups[group_id],prop,value)

		cycles = self.get_n_cycles_value()
		in_trigger = self.get_start_value()
		out_trigger = self.clicked_output_trigger.get()
		# inhibit = self.get_inhibit_value()

		setattr(self.profile,"cycles",cycles)
		setattr(self.profile,"in_trigger",in_trigger)
		setattr(self.profile,"out_trigger",out_trigger)

		self.configuration.profiles[self.profile.id] = self.profile


	def print_profile_button_action(self):

		self.edit_config_for_profile()

		for i in self.profile.groups:
			print(i)

	
	def build_multiplier_choices(self):

		pulse_block_names = ["TetrAMMs/Detectors", "Cam","Fluorescence","User"]

		pulse_column = 5
		
		for i in range(4): #4 pulse blocks

			ttk.Label(self, text =pulse_block_names[i]).grid(column =pulse_column, row = i, padx = 5,pady = 5 ,sticky="e" )
			self.multiplier_var = tk.StringVar(value=self.profile.multiplier[i])
			tk.Entry(self, bd =1, textvariable=self.multiplier_var).grid(column = pulse_column+1, row = i, padx = 5,pady = 5 ,sticky="w" )





	def __init__(self, notebook, configuration, n_profile, BeamlinePandaIO):

		self.notebook = notebook
		self.configuration = configuration
		self.n_profile = n_profile
		self.profile = self.configuration.profiles[self.n_profile]
		self.BeamlinePandaIO = BeamlinePandaIO

		self.seq_table = self.profile.seq_table()


		super().__init__(self.notebook,borderwidth=5, relief='raised')


		# self.tab = ttk.Frame(self.notebook,borderwidth=5, relief='raised') 
		self.notebook.add(self, text ='Profile '+str(self.profile.id))

		ttk.Label(self, text ='Profile '+str(self.profile.id)).grid(column =0, row = 0, padx = 5,pady = 5 ,sticky="w" )

		self.Columns = ["Groups","Frames","Wait Time", "Wait Units", "Run Time", "Run Units", "Wait Pause", "Run Pause", "Wait Pulses", "Run Pulses"]

		# self.start_label_list = ["Software", "\u2191 BM Trigger", "\u2191 ADC chan 0", "\u2191 ADC chan 1",
		# "\u2191 ADC chan 2", "\u2191 ADC chan 3", "\u2191 ADC chan 4", "\u2191 ADC chan 5", "\u2191 TTL trig 0",
		# "\u2191 TTL trig 1", "\u2191 TTL trig 2", "\u2191 TTL trig 3", "\u2191 LVDS Lemo ", "\u2191 TFG cable 1",
		# "\u2191 TFG cable 2", "\u2191 TFG cable 3", "\u2191 Var thrshld", "\u2193 BM Trigger",
		# "\u2193 ADC chan 0", "\u2193 ADC chan 1", "\u2193 ADC chan 2", "\u2193 ADC chan 3", "\u2193 ADC chan 4",
		# "\u2193 ADC chan 5", "\u2193 TTL trig 0", "\u2193 TTL trig 1", "\u2193 TTL trig 2", "\u2193 TTL trig 3",
		# "\u2193 LVDS Lemo", "\u2193 TFG cable 1", "\u2193 TFG cable 2", "\u2193 TFG cable 3",
		# "\u2193 Var thrshld"]


		# self.display_pause = ["Software", "No Pause", "\u2191 BM Trigger", "\u2191 ADC chan 0",
		# "\u2191 ADC chan 1", "\u2191 ADC chan 2", "\u2191 ADC chan 3", "\u2191 ADC chan 4", "\u2191 ADC chan 5",
		# "\u2191 TTL trig 0", "\u2191 TTL trig 1", "\u2191 TTL trig 2", "\u2191 TTL trig 3", "\u2191 LVDS Lemo ",
		# "\u2191 TFG cable 1", "\u2191 TFG cable 2", "\u2191 TFG cable 3", "\u2191 Var thrshld",
		# "\u2193 BM Trigger", "\u2193 ADC chan 0", "\u2193 ADC chan 1", "\u2193 ADC chan 2", "\u2193 ADC chan 3",
		# "\u2193 ADC chan 4", "\u2193 ADC chan 5", "\u2193 TTL trig 0", "\u2193 TTL trig 1", "\u2193 TTL trig 2",
		# "\u2193 TTL trig 3", "\u2193 LVDS Lemo", "\u2193 TFG cable 1", "\u2193 TFG cable 2", "\u2193 TFG cable 3",
		# "\u2193 Var thrshld"]


		self.outputs = self.profile.outputs()
		self.inputs = self.profile.inputs()

		self.build_multiplier_choices()

		self.default_group = Group(0, 1, 1, "ms", 1, "ms", False, False, [1,0,0,0,0,0,0,0], [1,0,0,0,0,0,0,0])

		# self.ins, self.outs = self.create_in_out_trigger()
		
		### add tree view ############################################
		
		self.build_profile_tree()

		############################################################

		##### input trigger select

		self.seq_triggers = self.profile.seq_triggers()
		# self.seq_triggers = [f.lower() for f in self.seq_triggers]

		ttk.Label(self, text ="Seq Trigger").grid(column =0, row = 0, padx = 5,pady = 5 ,sticky="e" )
		self.clicked_start_trigger = tk.StringVar()  
		ttk.OptionMenu(self , self.clicked_start_trigger , self.profile.in_trigger, *self.seq_triggers).grid(column =1, row = 0, padx = 5,pady = 5 ,sticky="w" )
		
		# self.clicked_start_trigger = tk.StringVar() 
		# starttrigger_dropdown = ttk.OptionMenu(self.tab , self.clicked_start_trigger , self.start_label_list[0]) 
		# starttrigger_dropdown.grid(column =1, row = 0, padx = 5,pady = 5 ,sticky="w" )
		# menu = starttrigger_dropdown["menu"]


		# software_sublist = tk.Menu(menu, tearoff=False)
		# menu.add_cascade(label="software", menu=software_sublist)
		# software_sublist.add_command(label = "software", command = lambda:self.clicked_start_trigger.set(in_trig))


		# ins_sublist = tk.Menu(menu, tearoff=False)
		# menu.add_cascade(label="ins", menu=ins_sublist)
		# for in_trig in self.ins:
		# 	# sublist.add_command(label = in_trig, command = lambda:self.clicked_start_trigge.set())
		# 	ins_sublist.add_command(label = in_trig, command = lambda:self.clicked_start_trigger.set(in_trig))


		# outs_sublist = tk.Menu(menu, tearoff=False)
		# menu.add_cascade(label="outs", menu=outs_sublist)
		# for out_trig in self.outs:
		# 	# sublist.add_command(label = in_trig, command = lambda:self.clicked_start_trigge.set())
		# 	outs_sublist.add_command(label = out_trig, command = lambda:self.clicked_start_trigger.set(out_trig))

		
		##### output trigger select

		ttk.Label(self, text ="Output Trigger").grid(column = 0, row = 2, padx = 5,pady = 5 ,sticky="e" )
		self.clicked_output_trigger = tk.StringVar() 
		ttk.OptionMenu(self , self.clicked_output_trigger , self.profile.out_trigger, *self.outputs).grid(column = 1, row = 2,padx = 5,pady = 5,sticky="w" )

		################# external inhibit select

		self.external_inhibit = tk.IntVar() 
		tk.Checkbutton(self, text = "External Inhibit", 
						variable = self.external_inhibit, 
						onvalue = 1, 
						offvalue = 0, 
						height = 2, 
						width = 20) .grid(column = 2, row = 0, padx = 5,pady = 5 ,sticky="w" )

		############# number of cycles box

		############# number of cycles box

		tk.Label(self, text="No. of cycles").grid(column = 3, row = 0, padx = 5,pady = 5 ,sticky="e" )
		self.n_cycles_entry_value = tk.IntVar(self, value=self.profile.cycles)
		tk.Entry(self, bd =1, textvariable=self.n_cycles_entry_value).grid(column = 4, row = 0, padx = 5,pady = 5 ,sticky="w" )

		############# plot button

		self.plot_profile_button = tk.Button(self, text ="Plot Profile", command = self.profile.plot_triggering).grid(column = 8, row = 0, padx = 5,pady = 5,columnspan=1, sticky='e')

		############# profile info

		self.generate_info_boxes()

		############profile settings
		self.insertrow_button = tk.Button(self, text ="Insert group", command = self.insert_group_button_action).grid(column = 0, row = 10, padx = 5,pady = 5,columnspan=1, sticky='w')
		self.appendrow_button = tk.Button(self, text ="Add group", command = self.append_group_button_action).grid(column = 1, row = 10, padx = 5,pady = 5,columnspan=1, sticky='w')
		self.deleterow_button = tk.Button(self, text ="Delete group", command = self.delete_group_button_action).grid(column = 2, row = 10, padx = 5,pady = 5,columnspan=1, sticky='w')
		self.deletefinalrow_button = tk.Button(self, text ="Discard group", command = self.delete_last_groups_button_action).grid(column = 2, row = 10, padx = 5,pady = 5,columnspan=1, sticky='e')

		self.print_profile_button = tk.Button(self, text ="Print Profile", command = self.print_profile_button_action).grid(column = 5, row = 10, padx = 5,pady = 5,columnspan=1, sticky='e')

		print(self.BeamlinePandaIO.PulseBlocks)

		for p,n_pulse_block in enumerate(self.BeamlinePandaIO.PulseBlocks.keys()):

			pulse_block_dets = self.BeamlinePandaIO.PulseBlocks[n_pulse_block]
			
			for n,n_det in enumerate(pulse_block_dets):

				device_name = self.BeamlinePandaIO.TTLOUT[n_det]

				det_on = tk.IntVar() 
				tk.Checkbutton(self, text = device_name, 
								variable = det_on, 
								onvalue = 1, 
								offvalue = 0, 
								height = 2, 
								width = 20).grid(column = 11+n, row = p*2, padx = 5,pady = 5 ,sticky="w" )


class PandaConfigBuilderGUI(tk.Tk):

	def theme(self, theme_name):

		style = ttk.Style(self.window)

		self.theme_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),"themes",theme_name+'.tcl')

		self.window.tk.eval(self.theme_dir)
		self.window.tk.call("package", "require", theme_name)
		print(style.theme_names())
		# --> ('awlight', 'clam', 'alt', 'default', 'awdark', 'classic')
		style.theme_use(theme_name)

	def add_profile_tab(self, event):

		if self.notebook.select() == self.notebook.tabs()[-1]:

			print("new profile tab created")

			self.notebook.forget(self.add_frame)

			default_configuration = PandaTriggerConfig.read_from_yaml(self.default_config_path)
			default_configuration.profiles[0].id = len(self.configuration.profiles)
			profile = default_configuration.profiles[0]

			self.configuration.append_profile(profile)

			new_profile_tab = ProfileTab(self.notebook, self.configuration, len(self.configuration.profiles)-1)

			self.notebook.add(new_profile_tab, text="Profile " + str(len(self.configuration.profiles)-1))

			self.add_frame = tk.Frame()
			self.notebook.add(self.add_frame, text="+")
			self.window.bind("<<NotebookTabChanged>>", self.add_profile_tab)

			for n,tab in enumerate(self.notebook.tabs()[0:-1]):
				self.notebook.tab(n, text='Profile '+str(n))

			self.delete_profile_button = tk.Button(new_profile_tab, text ="Delete Profile", command = self.delete_profile_tab).grid(column = 4, row = 10, padx = 5,pady = 5,columnspan=1, sticky='e')


	def delete_profile_tab(self):

		answer = tk.messagebox.askyesno("Close Profile", "Delete this profile? Are you sure?")

		if answer and (self.configuration.n_profiles >= 2):

			index_to_del = self.notebook.index("current")

			if index_to_del == 0:
				select_tab_index = 1
			else:
				select_tab_index = index_to_del-1

			self.notebook.select(self.notebook.tabs()[select_tab_index])
			self.configuration.delete_profile(index_to_del)
			self.notebook.forget(self.notebook.tabs()[index_to_del])
			
		elif answer and (self.configuration.n_profiles == 1):
			tk.messagebox.showinfo("Info","Must have atleast one profile")

		
		tab_names = self.notebook.tabs()

		for n,tab in enumerate(self.notebook.tabs()[0:-1]):
			self.notebook.tab(n, text='Profile '+str(n))
			proftab_object = self.notebook.nametowidget(tab_names[n])
			ttk.Label(proftab_object, text ='Profile '+str(n)).grid(column =0, row = 0, padx = 5,pady = 5 ,sticky="w" )

		
		return None
	
	def commit_config(self):

		tab_names = self.notebook.tabs()

		for i in range(self.configuration.n_profiles):

			proftab_object = self.notebook.nametowidget(tab_names[i])
			proftab_object.edit_config_for_profile()

		self.configuration.experiment = self.experiment_var.get()

	

	def load_config(self):
		
		panda_config_yaml = fd.askopenfilename()

		answer = tk.messagebox.askyesno("Close/Open New", "Finished editing this profile? Continue?") 

		if answer:
			self.window.destroy()
			PandaConfigBuilderGUI(panda_config_yaml)
		else:
			return

	def save_config(self):

		panda_config_yaml = fd.asksaveasfile(mode='w',defaultextension=".yaml",filetypes=[("yaml", ".yaml")])
		
		if panda_config_yaml:

			self.commit_config()
			self.configuration.save_to_yaml(panda_config_yaml.name)


	def show_start_value(self):
		self.selected_start_trigger = self.clicked_start_trigger.get()
		print(self.selected_start_trigger)


	def configure_panda(self):

		self.commit_config()
		index = self.notebook.index("current")
		profile_to_upload = self.configuration.profiles[index]
		seq_table = profile_to_upload.seq_table()
		n_cycles = profile_to_upload.cycles

		RE(modify_panda_seq_table(self.panda, seq_table, n_cycles, prescale_unit='us' ,n_seq=1))





	def open_textedit(self):

		try:
			os.system("/dls_sw/apps/atom/1.42.0/atom & ")
		except IOError:
			os.system("subl & ")
		except:
			os.system("gedit & ")


	def show_wiring_config(self):

		for key in self.BeamlinePandaIO.TTLIN.keys():
			INDev = self.BeamlinePandaIO.TTLIN[key]

			plt.scatter(0, key, color='k',s=50)
			plt.text(0+0.1, key, INDev)

		for key in self.BeamlinePandaIO.TTLOUT.keys():
			OUTDev = self.BeamlinePandaIO.TTLOUT[key]

			plt.scatter(1, key, color='b',s=50)
			plt.text(1+0.1, key, OUTDev)

		plt.ylabel("TTL I/O Connection")
		plt.grid()
		plt.xlim(-0.2,2)
		plt.show()

	def run_experiment(self):

		print(np.random.random())

		run_arm(beamline, device_name)


	def build_exp_run_frame(self):
		
		self.run_frame = ttk.Frame(self.window,borderwidth=5, relief='raised')
		self.run_frame.pack(fill ="both",expand=True, side="right")
		self.run_button = tk.Button(self.run_frame, text ="Run Sequence", command = self.run_experiment).grid(column = 2, row = 1, padx = 5,pady = 5,columnspan=1, sticky='news')


	def build_global_settings_frame(self):

		self.global_settings_frame = ttk.Frame(self.window,borderwidth=5, relief='raised')
		self.global_settings_frame.pack(fill ="both",expand=True, side="left")

		#add a load/save/configure button
		self.load_button = tk.Button(self.global_settings_frame, text ="Load", command = self.load_config).grid(column = 0, row = 0, padx = 5,pady = 5,columnspan=1,sticky="e")
		self.save_button = tk.Button(self.global_settings_frame, text ="Save", command = self.save_config).grid(column = 1, row = 0, padx = 5,pady = 5,columnspan=1,sticky="e")
		self.configure_button = tk.Button(self.global_settings_frame, text ="Upload to PandA", command = self.configure_panda).grid(column =2, row = 0, padx = 5,pady = 5,columnspan=1,sticky="e")

		self.show_wiring_config_button = tk.Button(self.global_settings_frame, text ="Wiring config", command = self.show_wiring_config).grid(column = 4, row = 0, padx = 5,pady = 5,columnspan=1)
		self.Opentextbutton = tk.Button(self.global_settings_frame, text ="Open Text Editor", command = self.open_textedit).grid(column = 2, row = 1, padx = 5,pady = 5,columnspan=1)


	def build_add_frame(self):

		self.add_frame = tk.Frame()
		self.notebook.add(self.add_frame, text="+")
		self.window.bind("<<NotebookTabChanged>>", self.add_profile_tab)

	
	def build_exp_info_frame(self):

		self.experiment_settings_frame = ttk.Frame(self.window,borderwidth=5, relief='raised')
		self.experiment_settings_frame.pack(fill ="both",expand=True, side="left",anchor="w")

		self.experiment_var = tk.StringVar(value=self.configuration.experiment)
		tk.Label(self.experiment_settings_frame, text ="Instrument: "+self.configuration.instrument.upper()).grid(column =0, row = 0, padx = 5,pady = 5 ,sticky="w" )
		tk.Label(self.experiment_settings_frame, text ="Experiment:").grid(column = 0, row = 1, padx = 5,pady = 5 ,sticky="w" )
		tk.Entry(self.experiment_settings_frame, bd =1, textvariable=self.experiment_var).grid(column = 1, row = 1, padx = 5,pady = 5 ,sticky="w" )
		
		# self.experiment_dir = tk.StringVar(value=self.configuration.data_dir)
		# tk.Label(self.experiment_settings_frame, text ="Save dir:").grid(column = 0, row = 2, padx = 5,pady = 5 ,sticky="w" )
		# tk.Entry(self.experiment_settings_frame, bd =1, textvariable=self.experiment_dir, width=30).grid(column = 1, row = 2, padx = 5,pady = 5 ,sticky="w" )


	def __init__(self,panda_config_yaml=None):

		try:
			self.panda = return_connected_device("i22", "panda1")
		except:
			answer = tk.messagebox.askyesno("PandA not Connected", "PandA is not connected, if you continue things will not work. Continue?")
			if answer:
				pass


		self.panda_config_yaml = panda_config_yaml
		self.default_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"default_panda_config.yaml")
		
		if self.panda_config_yaml == None:
			self.configuration = PandaTriggerConfig.read_from_yaml(self.default_config_path)
		else:
			self.configuration = PandaTriggerConfig.read_from_yaml(self.panda_config_yaml)

		
		if self.configuration.experiment == None:
			user_input = tk.simpledialog.askstring(title="Experiment",
                                  prompt="Enter an experiment code:")
			
			self.configuration.experiment = user_input


		self.default_ioconfig = os.path.join(os.path.dirname(os.path.realpath(__file__)),BL+"_panda_wiring.yaml")
		self.BeamlinePandaIO = PandaIO(self.default_ioconfig)

		self.profiles = self.configuration.profiles
		
		self.window = tk.Tk()
		self.window.resizable(1,1)
		self.window.minsize(600,200)

		self.build_exp_run_frame()



		self.window.title("Panda Config") 
		self.notebook = ttk.Notebook(self.window)
		self.notebook.pack(fill ="both",expand=True)

		for i in range(self.configuration.n_profiles):

			ProfileTab(self.notebook, self.configuration, i, self.BeamlinePandaIO)
			tab_names = self.notebook.tabs()
			proftab_object = self.notebook.nametowidget(tab_names[i])
			self.delete_profile_button = tk.Button(proftab_object, text ="Delete Profile", command = self.delete_profile_tab).grid(column = 4, row = 10, padx = 5,pady = 5,columnspan=1, sticky='e')

	
		########################################################
		self.build_exp_info_frame()
		######## #settings and buttons that apply to all profiles
		self.build_global_settings_frame()
		self.build_add_frame()
		#################################################################


		
		print("Uncomment this when you want to actually upload the panda interface")
		# run_upload_yaml_to_panda(beamline='i22')
		# print("upload complete")

		self.window.mainloop()







if __name__ == '__main__':

	# panda = HDFPanda()
	# print(panda.inenc[1])
	# quit()


	# print(3, decimal_to_binary(3))
	# print(192, decimal_to_binary(192))
	# quit()

	dir_path = os.path.dirname(os.path.realpath(__file__))
	print(dir_path)
	config_filepath = os.path.join(dir_path,"panda_config.yaml")
	PandaConfigBuilderGUI(config_filepath)
	# # quit()


	# panda_trigger = ConfigureTrigger(config_filepath)
	# panda_trigger.plot_triggering(1,confirm=True)

