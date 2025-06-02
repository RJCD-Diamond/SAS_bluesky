#!/dls/science/users/akz63626/i22/i22_venv/bin/python


"""

Python Elements for NCD PandA config GUI

"""

from pathlib import Path
import os
from importlib import import_module

import tkinter as tk
from tkinter import ttk

from ophyd_async.fastcs.panda import (
	SeqTrigger,
)
from ophyd_async.fastcs.panda._block import PandaTimeUnits

from dodal.utils import get_beamline_name

from ProfileGroups import Profile, Group
from utils.ncdcore import ncdcore




BL = get_beamline_name(os.environ['BEAMLINE'])
BL_config = import_module(f"beamline_configs.{BL}_config")

PULSEBLOCKS = BL_config.PULSEBLOCKS
THEME_NAME = BL_config.THEME_NAME
PULSEBLOCKASENTRYBOX = BL_config.PULSEBLOCKASENTRYBOX
PULSE_BLOCK_NAMES = BL_config.PULSE_BLOCK_NAMES

TTLIN = BL_config.TTLIN
TTLOUT = BL_config.TTLOUT


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


	# def focus_out_generate_info_boxes(event):
	    
	# 	self.generate_info_boxes()

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

		# cycles_entry.bind("<FocusOut>", self.focus_out_generate_info_boxes)


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

