#!/dls/science/users/akz63626/i22/i22_venv/bin/python


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

# from dodal.beamlines import module_name_for_beamline
from dodal.common.beamlines.beamline_utils import set_beamline as set_utils_beamline
from dodal.log import set_beamline as set_log_beamline
from dodal.utils import BeamlinePrefix, get_beamline_name
# from dodal.utils import make_device
# try:
# 	from dodal.plans.save_panda import _save_panda 
# except:
# 	print("save_device has been deprecated and removed! Perhaps ophyd_async.plan_stubs.store_settings")

from pprint import pprint

# from ophyd_async.core import DetectorTrigger, TriggerInfo, wait_for_value, in_micros
from ophyd_async.fastcs.panda import (
	HDFPanda,
	SeqTable,
	SeqTrigger,
	SeqBlock
)

try:
	from ophyd_async.fastcs.panda._block import PandaTimeUnits
except:
	from ophyd_async.fastcs.panda import TimeUnits


from dodal.beamlines.i22 import panda1
from blueapi.client.client import BlueapiRestClient, BlueapiClient
from blueapi.config import RestConfig


import bluesky.plan_stubs as bps

from ProfileGroups import Profile, Group, PandaTriggerConfig
from ncdcore import ncdcore


__version__ = '0.1'
__author__ = 'Richard Dixey'

############################################################################################


try:
	BL = get_beamline_name(os.environ['BEAMLINE'])
except:
	BL = "i22"
	print("Defaulting to i22")


PULSEBLOCKS = 4
PULSEBLOCKASENTRYBOX = False
PULSE_BLOCK_NAMES = ["FS", "DETS/TETS","OAV","Fluro"]
THEME_NAME = "clam"
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
		self.TTLOUT = self.wiring_config["TTLOUT"]
		self.LVDSIN= self.wiring_config["LVDSIN"]
		self.LVDSOUT = self.wiring_config["LVDSOUT"]
		self.PulseBlocks = self.wiring_config["PulseBlocks"]


##################################################################

default_ioconfig = os.path.join(os.path.dirname(os.path.realpath(__file__)),BL+"_panda_wiring.yaml")
BeamlinePandaIO = PandaIO(default_ioconfig)


############################################################################################

class EditableTableview(ttk.Treeview):
	
	def __init__(self, parent, *args, **kwargs):

		self.parent = parent
		super().__init__(parent, *args, **kwargs)
		self.bind("<Double-1>", lambda event: self.onDoubleClick(event))
		self.kwargs = kwargs		

	def onDoubleClick(self, event):
		''' Executed, when a row is double-clicked. Opens 
		read-only EntryPopup above the item's column, so it is possible
		to select text '''

		# close previous popups
		try:  # in case there was no previous popup
			self.Popup.destroy()
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
			options = list(PandaTimeUnits.__dict__["_member_names_"])
			# options = [f.lower() for f in options]

			self.Popup = DropdownPopup(self, rowid, int(column[1:])-1, text, options)
			self.Popup.place(x=x, y=y+pady, width=width, height=height, anchor='w')

		elif column in ["#7"]: #these groups create a drop down menu

			# place dropdown popup properly

			TTLIN = list(BeamlinePandaIO.TTLIN)
			TTLIN = [f"TTLIN{f}" for f in TTLIN]
			LVDSIN = list(BeamlinePandaIO.LVDSIN)
			LVDSIN = [f"LVDSIN{f}" for f in LVDSIN]

			options = list(SeqTrigger.__dict__["_member_names_"])

			# options = ["True", "False"]
			self.Popup = DropdownPopup(self, rowid, int(column[1:])-1, text, options)
			self.Popup.place(x=x, y=y+pady, width=width, height=height, anchor='w')


		elif (column in ["#8", "#9"]):

			if (PULSEBLOCKASENTRYBOX == False):
				self.Popup = CheckButtonPopup(self, rowid, int(column[1:])-1, x=x,y=y, columns=self.kwargs["columns"])
			if (PULSEBLOCKASENTRYBOX == True):
				self.Popup = EntryPopup(self, rowid, int(column[1:])-1, text, entrytype=list)
				self.Popup.place(x=x, y=y+pady, width=width, height=height, anchor='w')

		else:

			# place Entry popup properly
			self.Popup = EntryPopup(self, rowid, int(column[1:])-1, text, entrytype=int)
			self.Popup.place(x=x, y=y+pady, width=width, height=height, anchor='w')

		return

class DropdownPopup(ttk.Combobox):
	def __init__(self, parent, rowid, column, text, options, **kw):
		ttk.Style().configure('pad.TEntry', padding='1 1 1 1')

		self.option_var = tk.StringVar()
		self.tv = parent
		self.rowid = rowid
		self.column = column

		super().__init__(parent, textvariable=self.option_var, values=options, state="readonly")

		self.current(options.index(text)) 

		# self.event_generate('<Button-1>')

		self.bind("<Return>", self.on_return)
		self.bind("<Escape>", lambda *ignore: self.destroy())
		self.bind('<<ComboboxSelected>>', self.on_return )
		self.focus_force()


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

		self.tv.parent.parent.commit_config()
		self.tv.parent.profile.analyse_profile()
		self.tv.parent.generate_info_boxes()


class CheckButtonPopup(ttk.Checkbutton):
	def __init__(self, parent, rowid, column, x,y, columns, **kw):

		self.parent = parent
		self.rowid = rowid
		self.column = column

		self.row_num = int(rowid[-2::], 16)-1

		w = 420 # width for the Tk root
		h = 50 # height for the Tk root

		self.root = tk.Toplevel() ##HOLY MOLY - THIS WAS TK.TK AND IT WAS CAUSING SO MANY ISSUES, USE TOPLEVEL WHEN OPENING NEW TEMP WINDOW. IT WAS CUASING THE CHECKBUTTON TO ASSIGN TO SOMETHING ELSE. SEE https://stackoverflow.com/questions/55208876/tkinter-set-and-get-not-working-in-a-window-inside-a-window
		self.root.minsize(w,h)
		self.root.title(f"{columns[column]} - Group: {self.row_num}")

		vals = self.parent.item(self.rowid, 'values')
		self.vals = list(vals)
		self.pulse_vals = self.vals[self.column].split()

		self.option_var = {}
		self.checkbuttons = {}

		self.create_checkbuttons()

		# get screen width and height
		ws = self.root.winfo_screenwidth() # width of the screen
		hs = self.root.winfo_screenheight() # height of the screen

		# calculate x and y coordinates for the Tk root window
		x = (ws/2) - (w/2) + x/2
		y = (hs/2) - (h/2) + y/2

		# set the dimensions of the screen 
		# and where it is placed
		self.root.geometry('%dx%d+%d+%d' % (w, h, x-60, y))
		self.save_pulse_button = ttk.Button(self.root, text ="Ok", command = self.on_return).grid(column = PULSEBLOCKS, row = 0, padx = 5,pady = 5,columnspan=1, sticky='e')

		self.root.protocol("WM_DELETE_WINDOW", self.abort)
		self.root.bind("<Escape>", lambda *ignore: self.destroy())

	def create_checkbuttons(self):

		for pulse in range(PULSEBLOCKS):

			value = ncdcore.str2bool(str(self.pulse_vals[pulse]))
			var = tk.IntVar(value=int(value))

			self.option_var[pulse] = var

			CB = tk.Checkbutton(self.root, text=f"Pulse: {pulse}", variable=self.option_var[pulse], command=lambda pulse=pulse: self.toggle(pulse), onvalue=1, offvalue=0)
			CB.var = self.option_var[pulse]
			CB.grid(column = pulse, row = 0, padx = 5,pady = 5,columnspan=1)

			self.option_var[pulse].set(1)

			self.checkbuttons[pulse] = CB

			if value == 1:
				self.checkbuttons[pulse].select()
			else:
				self.checkbuttons[pulse].deselect()

	def toggle(self, pulse):

		if self.option_var[pulse].get() == 1:
			self.option_var[pulse].set(1)
		else:
			self.option_var[pulse].set(0)


	def abort(self):

		self.root.destroy()
		del self

	def on_return(self):

		for pulse in range(PULSEBLOCKS):
			val = str(self.option_var[pulse].get())
			self.pulse_vals[pulse] = val

		self.pulse_vals = " ".join(self.pulse_vals)

		self.vals[self.column] = self.pulse_vals

		self.parent.item(self.rowid, values=self.vals)
		self.root.destroy()
		del self



class EntryPopup(ttk.Entry):
	def __init__(self, parent, iid, column, text, entrytype=int, **kw):
		ttk.Style().configure('pad.TEntry', padding='1 1 1 1')
		super().__init__(parent, style='pad.TEntry', **kw)
		self.tv = parent
		self.iid = iid
		self.column = column
		self.entrytype = entrytype
		self.insert(0, text) 
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
		elif self.entrytype == list:
			selection = [str(int((f))) for f  in self.get().split()]
			selection = ' '.join(selection)
		else:
			selection = self.get()
			
		vals[self.column] = selection

		self.selection = selection

		self.tv.item(rowid, values=vals)
		self.destroy()

		self.tv.parent.parent.commit_config()
		self.tv.parent.profile.analyse_profile()
		self.tv.parent.generate_info_boxes()



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

			print(row)

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

		self.profile.append_group(Group=self.default_group)
		self.build_profile_tree()
		self.generate_info_boxes()



	def build_profile_tree(self):

		COLUMN_NAMES = list(self.profile.groups[0].__dict__.keys())[0:8]
		COLUMN_NAMES = [f.replace('_',' ').title() for f in COLUMN_NAMES]
		COLUMN_NAMES.insert(0, "Group ID")  # Add Group ID as the first column

		# print(self.profile.groups[0].__dict__.keys())

		if not hasattr(self, 'profile_config_tree'):
			self.profile_config_tree = EditableTableview(self, columns=COLUMN_NAMES, show="headings")
		else:
			del self.profile_config_tree
			self.profile_config_tree = EditableTableview(self, columns=COLUMN_NAMES, show="headings")

		table_row = 5
		widths = [100,100,150,150,150,150,150,150,150]

		#add the columns headers
		for i, col in enumerate(COLUMN_NAMES):
			self.profile_config_tree.heading(i, text=col)
			self.profile_config_tree.column(i, minwidth=widths[i], width=widths[i], stretch=True, anchor="w")

		# Insert sample data into the Treeview
		for i in range(len(self.profile.groups)):
			group_dict = (self.profile.groups[i].__dict__)
			group_list = list(group_dict.values())[0:len(COLUMN_NAMES)]
			group_list.insert(0, i)
			self.profile_config_tree.insert("", "end", values=group_list)

		self.profile_config_tree.grid(column = 0, row = table_row,padx = 5,pady = 5,columnspan=len(COLUMN_NAMES),rowspan=5)
		# self.profile_config_tree.bind("<Double-1>", lambda event: self.onDoubleClick(event))

		verscrlbar = ttk.Scrollbar(self, 
                           orient ="vertical", 
                           command = self.profile_config_tree.yview)
 
		verscrlbar.grid(column = len(widths), row = table_row, padx = 0,pady = 0, columnspan=1, rowspan=5, sticky='ns')
		
		# Configuring treeview
		self.profile_config_tree.configure(yscrollcommand = verscrlbar.set)

		############################################################


	def generate_info_boxes(self):
		try:

			self.total_frames_label.config(text=f"Total Frames: {self.profile.total_frames}")
			self.total_time_per_cycle.config(text=f"Time/cycle: {self.profile.duration_per_cycle:.3f} s")
			self.total_time_label.config(text=f"Total time: {self.profile.duration_per_cycle*self.profile.cycles:.3f} s")

		except:

			#### total frames
			self.total_frames_label = ttk.Label(self, text=f"Total Frames: {self.profile.total_frames}")
			self.total_frames_label.grid(column = 8, row = 1, padx = 5,pady = 5 ,sticky="e" )
			
			self.total_time_per_cycle = ttk.Label(self, text=f"Time/cycle: {self.profile.duration_per_cycle:.3f} s")
			self.total_time_per_cycle.grid(column = 8, row = 2, padx = 5,pady = 5 ,sticky="e" )

			### total time

			self.total_time_label = ttk.Label(self, text=f"Total time: {self.profile.duration_per_cycle*self.profile.cycles:.3f} s")
			self.total_time_label.grid(column = 8, row = 3, padx = 5,pady = 5 ,sticky="e" )

	
	def edit_config_for_profile(self):

		group_list = []

		for group_id, group_rowid in enumerate(self.profile_config_tree.get_children()):
			group = (self.profile_config_tree.item(group_rowid)["values"])
			
			n_group =  Group(frames=int(group[1]), 
							wait_time=int(group[2]), 
							wait_units=group[3], 
							run_time=int(group[4]), 
							run_units=group[5],
							pause_trigger=group[6], 
							wait_pulses=[int(f) for f in list(group[7].replace(" ",""))], 
							run_pulses=[int(f) for f in list(group[8].replace(" ",""))])
			
			group_list.append(n_group)

		cycles = self.get_n_cycles_value()
		profile_trigger = self.get_start_value()
		multiplier = [int(f.get()) for f in self.multiplier_var_options]
		out_trigger = "Dunno"

		new_profile = Profile(profile_id=self.profile.profile_id, 
						cycles=cycles, 
						seq_trigger=profile_trigger, 
						out_trigger=out_trigger, 
						groups=group_list, 
						multiplier=multiplier)
		
		self.profile = new_profile
		self.configuration.profiles[self.profile.profile_id] = new_profile



	def print_profile_button_action(self):
		
		self.parent.commit_config()
		self.profile.analyse_profile()
		self.generate_info_boxes()

		print(self.profile)

		for i in self.profile.groups:
			print(i)

	
	def build_multiplier_choices(self):


		pulse_column = 5

		self.multiplier_var_options = []

		ttk.Label(self, text ="Multipliers:").grid(column = 2, row = 0, padx = 5,pady = 5 ,sticky="news" )

		
		for i in range(PULSEBLOCKS): #4 pulse blocks

			col_pos = i+3

			ttk.Label(self, text =f"{PULSE_BLOCK_NAMES[i]}:").grid(column = col_pos, row = 0, padx = 5,pady = 5 ,sticky="nsw" )
			self.multiplier_var = tk.StringVar(value=self.profile.multiplier[i])
			tk.Entry(self, bd =1, width=10, textvariable=self.multiplier_var).grid(column = col_pos, row = 0, padx = 5,pady = 5 ,sticky="nes" )
			self.multiplier_var_options.append(self.multiplier_var)

	def commit_and_plot(self):

		# self.edit_config_for_profile()
		self.parent.commit_config()
		self.profile.plot_triggering()


	def focus_out_generate_info_boxes(event):
	    
		self.generate_info_boxes()

	def __init__(self, parent, notebook, configuration, n_profile):

		self.notebook = notebook
		self.parent = parent


		self.configuration = configuration
		self.n_profile = n_profile
		self.profile = self.configuration.profiles[self.n_profile]

		self.seq_table = self.profile.seq_table()


		super().__init__(self.notebook,borderwidth=5, relief='raised')

		self.notebook.add(self, text ='Profile '+str(self.profile.profile_id))

		self.columnconfigure(tuple(range(60)), weight=1)
		self.rowconfigure(tuple(range(30)), weight=1)

		ttk.Label(self, text ='Profile '+str(self.profile.profile_id)).grid(column =0, row = 0, padx = 5,pady = 5 ,sticky="w" )

		self.outputs = self.profile.outputs()
		self.inputs = self.profile.inputs()

		self.build_multiplier_choices()

		self.default_group  = Group(frames=1, 
				wait_time=1, 
				wait_units="MS", 
				run_time=1, 
				run_units="MS",
				pause_trigger="IMMEDIATE", 
				wait_pulses=[1,0,0,0], 
				run_pulses=[1,0,0,0])
		
		### add tree view ############################################
		
		self.build_profile_tree()

		############################################################

		##### input trigger select

		self.seq_triggers = self.profile.seq_triggers()
		# self.seq_triggers = [f.lower() for f in self.seq_triggers]

		ttk.Label(self, text ="Seq Trigger").grid(column =0, row = 0, padx = 5,pady = 5 ,sticky="e")
		self.clicked_start_trigger = tk.StringVar()  
		ttk.OptionMenu(self , self.clicked_start_trigger , self.profile.seq_trigger, *self.seq_triggers).grid(column =1, row = 0, padx = 5,pady = 5 ,sticky="w" )
		
		############# number of cycles box

		ttk.Label(self, text="No. of cycles").grid(column = 0, row = 1, padx = 5,pady = 5 ,sticky="e" )
		self.n_cycles_entry_value = tk.IntVar(self, value=self.profile.cycles)
		cycles_entry = tk.Entry(self, bd =1, width=15, textvariable=self.n_cycles_entry_value)
		cycles_entry.grid(column = 1, row = 1, padx = 5,pady = 5 ,sticky="w" )

		cycles_entry.bind("<FocusOut>", self.focus_out_generate_info_boxes)


		############# plot button
		############# profile info

		self.generate_info_boxes()

		############profile settings
		self.plot_profile_button = ttk.Button(self, text ="Plot Profile", command = self.commit_and_plot)
		self.insertrow_button = ttk.Button(self, text ="Insert group", command = self.insert_group_button_action)
		self.deleterow_button = ttk.Button(self, text ="Delete group", command = self.delete_group_button_action)
		self.appendrow_button = ttk.Button(self, text ="Add group", command = self.append_group_button_action)
		self.deletefinalrow_button = ttk.Button(self, text ="Discard group", command = self.delete_last_groups_button_action)
		self.print_profile_button = ttk.Button(self, text ="Print Profile", command = self.print_profile_button_action)
		
		self.plot_profile_button.grid(column = 8, row = 0, padx = 5,pady = 5,columnspan=1, sticky='nes')
		self.insertrow_button.grid(column = 0, row = 10, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.deleterow_button.grid(column = 1, row = 10, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.appendrow_button.grid(column = 3, row = 10, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.deletefinalrow_button.grid(column = 4, row = 10, padx = 5,pady = 5,columnspan=1, sticky='news')
		
		self.print_profile_button.grid(column = 3, row = 1, padx = 5,pady = 5,columnspan=1, sticky='nes')


class PandaConfigBuilderGUI(tk.Tk):

	def theme(self, theme_name):

		style = ttk.Style(self.window)

		print(style.theme_names())

		style.theme_use(THEME_NAME)

		self.theme_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),"themes",theme_name+'.tcl')

		# self.window.tk.eval(self.theme_dir)
		# self.window.tk.call("package", "require", theme_name)
		# --> ('awlight', 'clam', 'alt', 'default', 'awdark', 'classic')

	def add_profile_tab(self, event):

		if self.notebook.select() == self.notebook.tabs()[-1]:

			print("new profile tab created")

			self.notebook.forget(self.add_frame)

			default_configuration = PandaTriggerConfig.read_from_yaml(self.default_config_path)
			# default_configuration.profiles[0].group_id = len(self.configuration.profiles)
			profile = default_configuration.profiles[0]

			self.configuration.append_profile(profile)

			new_profile_tab = ProfileTab(self, self.notebook, self.configuration, len(self.configuration.profiles)-1)

			self.notebook.add(new_profile_tab, text="Profile " + str(len(self.configuration.profiles)-1))

			self.add_frame = tk.Frame()
			self.notebook.add(self.add_frame, text="+")
			self.window.bind("<<NotebookTabChanged>>", self.add_profile_tab)

			for n,tab in enumerate(self.notebook.tabs()[0:-1]):
				self.notebook.tab(n, text='Profile '+str(n))

			self.delete_profile_button = ttk.Button(new_profile_tab, text ="Delete Profile", command = self.delete_profile_tab)
			self.delete_profile_button.grid(column = 7, row = 10, padx = 5,pady = 5,columnspan=1, sticky='news')

			self.notebook.select(self.notebook.tabs()[-2])


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
		self.seq_table = profile_to_upload.seq_table()

		try:
			run_upload_yaml_to_panda(beamline='i22')
		except:
			print("could not upload yaml to panda")

		try:
			run_modify_panda_seq_table('i22', "panda1", self.seq_table, n_seq=1)
		except:
			print("could not modify panda seq table")


	def open_textedit(self):

		if os.path.exists("/dls_sw/apps/atom/1.42.0/atom"):
			os.system("/dls_sw/apps/atom/1.42.0/atom "+ self.panda_config_yaml + " &")
		else:
			try:
				os.system("subl "+ self.panda_config_yaml + " &")
			except:
				os.system("gedit "+ self.panda_config_yaml + " &")


	def show_wiring_config(self):

		fig, ax = plt.subplots(1,1, figsize=(16, 8))

		labels= ["TTLIN", "LVDSIN","TTLOUT", "LVDSOUT"]

		for key in self.BeamlinePandaIO.TTLIN.keys():
			INDev = self.BeamlinePandaIO.TTLIN[key]

			ax.scatter(0, key, color='k',s=50)
			ax.text(0+0.1, key, INDev)

		for key in self.BeamlinePandaIO.LVDSIN.keys():
			LVDSINDev = self.BeamlinePandaIO.LVDSIN[key]

			ax.scatter(1, key, color='k',s=50)
			ax.text(1+0.1, key, LVDSINDev)

		for key in self.BeamlinePandaIO.TTLOUT.keys():
			TTLOUTDev = self.BeamlinePandaIO.TTLOUT[key]

			ax.scatter(2, key, color='b',s=50)
			ax.text(2+0.1, key, TTLOUTDev)

		for key in self.BeamlinePandaIO.LVDSOUT.keys():
			LVDSOUTDev = self.BeamlinePandaIO.LVDSOUT[key]
			ax.scatter(3, key, color='b',s=50)
			ax.text(3+0.1, key, LVDSOUTDev)

		ax.set_ylabel("I/O Connections")
		ax.grid()
		ax.set_xlim(-0.2,4)
		plt.gca().invert_yaxis()
		ax.set_xticks(range(len(labels)))
		ax.set_xticklabels(labels, rotation=90)
		plt.show()

	def get_plans(self):

		plans = self.client.get_plans().plans

		for plan in plans:
			print(plan,"\n\n")

	def get_devices(self):

		devices = (self.client.get_devices().devices)
		
		for dev in devices:
			print(dev,"\n\n")

	def stop_plans(self):

		self.client.stop()

	def pause_plans(self):

		self.client.pause()

	def resume_plans(self):

		self.client.resume()

	# def run_plan(self):

	# 	print(self.client.get_plans())


	def build_exp_run_frame(self):
		
		self.run_frame = ttk.Frame(self.window,borderwidth=5, relief='raised')
		self.run_frame.pack(fill ="both",expand=True, side="right")
		self.get_plans_button = ttk.Button(self.run_frame, text ="Get Plans", command = self.get_plans).grid(column = 2, row = 1, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.get_devices_button = ttk.Button(self.run_frame, text ="Get Devices", command = self.get_devices).grid(column = 2, row = 3, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.stop_plans_button = ttk.Button(self.run_frame, text ="Stop Plan", command = self.stop_plans).grid(column = 2, row = 5, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.pause_plans_button = ttk.Button(self.run_frame, text ="Pause Plan", command = self.pause_plans).grid(column = 2, row = 7, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.resume_plans_button = ttk.Button(self.run_frame, text ="Resume Plan", command = self.resume_plans).grid(column = 2, row = 9, padx = 5,pady = 5,columnspan=1, sticky='news')

	def build_global_settings_frame(self):

		self.global_settings_frame = ttk.Frame(self.window,borderwidth=5, relief='raised')
		self.global_settings_frame.pack(fill ="both",expand=True, side="bottom")

		#add a load/save/configure button
		self.load_button = ttk.Button(self.global_settings_frame, text ="Load", command = self.load_config)
		self.save_button = ttk.Button(self.global_settings_frame, text ="Save", command = self.save_config)
		self.configure_button = ttk.Button(self.global_settings_frame, text ="Upload to PandA", command = self.configure_panda)
		self.show_wiring_config_button = ttk.Button(self.global_settings_frame, text ="Wiring config", command = self.show_wiring_config)
		self.Opentextbutton = ttk.Button(self.global_settings_frame, text ="Open Text Editor", command = self.open_textedit)

		self.load_button.pack(fill ="both",expand=True, side="left")
		self.save_button.pack(fill ="both",expand=True, side="left")
		self.configure_button.pack(fill ="both",expand=True, side="left")
		self.show_wiring_config_button.pack(fill ="both",expand=True, side="left")
		self.Opentextbutton.pack(fill ="both",expand=True, side="left")



	def build_add_frame(self):

		self.add_frame = tk.Frame()
		self.notebook.add(self.add_frame, text="+")
		self.window.bind("<<NotebookTabChanged>>", self.add_profile_tab)

	
	def build_exp_info_frame(self):

		self.experiment_settings_frame = ttk.Frame(self.window,borderwidth=5, relief='raised')
		self.experiment_settings_frame.pack(fill ="both",expand=True, side="bottom",anchor="w")

		self.experiment_var = tk.StringVar(value=self.configuration.experiment)
		ttk.Label(self.experiment_settings_frame, text ="Instrument: "+self.configuration.instrument.upper()).grid(column =0, row = 0, padx = 5,pady = 5 ,sticky="w" )
		ttk.Label(self.experiment_settings_frame, text ="Experiment:").grid(column = 0, row = 1, padx = 5,pady = 5 ,sticky="w" )
		tk.Entry(self.experiment_settings_frame, bd =1, textvariable=self.experiment_var).grid(column = 1, row = 1, padx = 5,pady = 5 ,sticky="w" )
		


	def build_active_detectors_frame(self):

		self.active_detectors_frames = {}

		for pulse in range(PULSEBLOCKS):

			active_detectors_frame_n = ttk.Frame(self.pulse_frame,borderwidth=5, relief='raised')
			active_detectors_frame_n.pack(fill ="both",expand=True, side="left",anchor="w")


			Pulselabel = ttk.Label(active_detectors_frame_n, text =f"Pulse Block: {pulse+1}")
			Pulselabel.grid(column =0, row = 0, padx = 5,pady = 5 ,sticky="w" )

			# if pulse == 0:
			TTLLabel = ttk.Label(active_detectors_frame_n, text =f"TTL:")
			TTLLabel.grid(column =0, row = 1, padx = 5,pady = 5 ,sticky="w" )

			for n, det in enumerate(self.BeamlinePandaIO.PulseBlocks[pulse+1]["TTLOUT"]):

				det_name = self.BeamlinePandaIO.TTLOUT[det]

				Outlabel = ttk.Label(active_detectors_frame_n, text =f"Out: {det}")
				Outlabel.grid(column =n+1, row = 0, padx = 5,pady = 5 ,sticky="w" )

				experiment_var = tk.StringVar(value=self.configuration.experiment)

				if (det_name.lower() == "fs") or ("shutter" in det_name.lower()):
					ad_entry = tk.Checkbutton(active_detectors_frame_n, bd =1, text=det_name, state='disabled')
					ad_entry.select()
				else:
					ad_entry = tk.Checkbutton(active_detectors_frame_n, bd =1, text=det_name)

				ad_entry.grid(column = n+1, row = 1, padx = 5,pady = 5 ,sticky="w" )

	def build_pulse_frame(self):

		self.pulse_frame = ttk.Frame(self.window, borderwidth=5, relief='raised')
		self.pulse_frame.pack(fill ="both",side='left',expand=True)
		Outlabel = ttk.Label(self.pulse_frame, text =f"Enable Device")
		Outlabel.pack(fill ="both",side='top',expand=True)


	def __init__(self,panda_config_yaml=None):

		if os.environ.get('USER') != "akz63626": #check if I am runing this

			try:
				self.panda = return_connected_device("i22", "panda1")
			except:
				answer = tk.messagebox.askyesno("PandA not Connected", "PandA is not connected, if you continue things will not work. Continue?")
				if answer:
					pass
				else:
					quit()


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


		# from tkinter import ttk  # Normal Tkinter.* widgets are not themed!
		# from ttkthemes import ThemedTk

		# self.window = ThemedTk(theme="arc")
		
		self.window = tk.Tk()
		self.window.resizable(1,1)
		self.window.minsize(600,200)
		self.theme("clam")

		menubar = tk.Menu(self.window)
		filemenu = tk.Menu(menubar, tearoff=0)
		filemenu.add_command(label="New", command=self.window.quit)
		filemenu.add_command(label="Open", command=self.window.quit)
		filemenu.add_command(label="Save", command=self.window.quit)
		filemenu.add_separator()
		filemenu.add_command(label="Exit", command=self.window.quit)
		menubar.add_cascade(label="File", menu=filemenu)

		helpmenu = tk.Menu(menubar, tearoff=0)
		helpmenu.add_command(label="Help Index", command=self.window.quit)
		helpmenu.add_command(label="About...", command=self.window.quit)
		menubar.add_cascade(label="Help", menu=helpmenu)

		self.window.config(menu=menubar)

		# style = ttk.Style()
		# style.configure("BW.TLabel", foreground="blue", background="black")

		# self.window.tk.call("source", "azure.tcl")
		# self.window.tk.call("set_theme", "light")

		# theme_name = "awdark"

		# style = ttk.Style()
		# self.windo.tk.call('lappend', 'auto_path', './theme')
		# self.window.tk.call('package', 'require', 'awthemes')
		# self.window.tk.call('::themeutils::setHighlightColor', 'awdark', '#007000')
		# self.window.tk.call('package', 'require', 'awdark')
		# style.theme_use('awdark')



		self.build_exp_run_frame()


		self.window.title("PandA Config") 
		self.notebook = ttk.Notebook(self.window)
		self.notebook.pack(fill ="both",side='top',expand=True)



		for i in range(self.configuration.n_profiles):

			ProfileTab(self, self.notebook, self.configuration, i)
			tab_names = self.notebook.tabs()
			proftab_object = self.notebook.nametowidget(tab_names[i])
			self.delete_profile_button = ttk.Button(proftab_object, text ="Delete Profile", command = self.delete_profile_tab)
			self.delete_profile_button.grid(column = 7, row = 10, padx = 5,pady = 5,columnspan=1, sticky='news')


		########################################################
		self.build_exp_info_frame()
		######## #settings and buttons that apply to all profiles
		self.build_global_settings_frame()

		self.build_pulse_frame()
		self.build_active_detectors_frame()



		self.build_add_frame()
		#################################################################


		# from blueapi.config import RestConfig
		# from blueapi.client.rest import BlueapiRestClient
		self.config = RestConfig(host=f"{BL}-blueapi.diamond.ac.uk", port=443, protocol="https")
		self.rest_client = BlueapiRestClient(self.config)
		self.client = BlueapiClient(self.rest_client)
	
		self.window.mainloop()




if __name__ == '__main__':

	#https://github.com/DiamondLightSource/blueapi/blob/main/src/blueapi/client/client.py <- use this to do stuff

	

	dir_path = os.path.dirname(os.path.realpath(__file__))
	print(dir_path)
	config_filepath = os.path.join(dir_path,"panda_config.yaml")
	PandaConfigBuilderGUI(config_filepath)

