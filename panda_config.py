import numpy as np
import argparse, os
import pandas as pd
import yaml
from datetime import datetime
from dataclasses import dataclass
import matplotlib.pyplot as plt

import xml.etree.ElementTree as ET

import time

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd


pd.set_option('display.max_columns', 999)  # or 1000
pd.set_option('display.max_rows', 999)  # or 1000
pd.set_option('display.max_colwidth', 999)  # or 199
pd.set_option('display.width',1000)


############################################################################################


"""
	
Useful functions

"""



def decimal_to_binary(n,bits=8): 
	"""
	(decimal_to_binary(192)
	
	gives 11000000

	"""
	binary_string =  bin(n).replace("0b", "")
	leading_zeros =  (int(bits-len(binary_string))*["0"])
	leading_zeros = "".join(leading_zeros)

	return leading_zeros+binary_string

def binary_to_decimal(n) -> int:
	"""
	binary_to_decimal("11000000")

	gives 192

	"""
	return int(n,2)



def to_seconds(unit: str) -> float:

	"""
	
	takes a unit and gives back the unit in normalised to seoncds


	eg to_seconds("msec") = 1e-3 #(in seconds)

	"""

	time_units = {"ns": 1e-9, "nsec": 1e-9, "usec": 1e-6, "ms": 1e-3, "msec": 1e-3,
		"s": 1, "sec": 1, "min": 60, "m": 60, "hour": 60*60, "h": 60*60 }

	return time_units[unit]


def start_methods(unit: int) -> str:

	"""
	
	takes a start method number and gives back the actual start method


	eg to_seconds("msec") = 1e-3 #(in seconds)

	"""

	# start_methods = {"ns": 1e-9, "nsec": 1e-9, "usec": 1e-6, "ms": 1e-3, "msec": 1e-3,
	# 	"s": 1, "sec": 1, "min": 60, "m": 60, "hour": 60*60, "h": 60*60 }

	start_label_list = [ "Software", "\u2191 BM Trigger", "\u2191 ADC chan 0", "\u2191 ADC chan 1",
		"\u2191 ADC chan 2", "\u2191 ADC chan 3", "\u2191 ADC chan 4", "\u2191 ADC chan 5", "\u2191 TTL trig 0",
		"\u2191 TTL trig 1", "\u2191 TTL trig 2", "\u2191 TTL trig 3", "\u2191 LVDS Lemo ", "\u2191 TFG cable 1",
		"\u2191 TFG cable 2", "\u2191 TFG cable 3", "\u2191 Var thrshld", "\u2193 BM Trigger",
		"\u2193 ADC chan 0", "\u2193 ADC chan 1", "\u2193 ADC chan 2", "\u2193 ADC chan 3", "\u2193 ADC chan 4",
		"\u2193 ADC chan 5", "\u2193 TTL trig 0", "\u2193 TTL trig 1", "\u2193 TTL trig 2", "\u2193 TTL trig 3",
		"\u2193 LVDS Lemo", "\u2193 TFG cable 1", "\u2193 TFG cable 2", "\u2193 TFG cable 3",
		"\u2193 Var thrshld"]

	start_methods = dict(zip( range(len(start_label_list)), start_label_list ))

	return start_methods[unit]



def str2bool(v):
  if str(v).lower() in ("y", "yes", "True", "true", "t", "1"):
  	return True
  elif str(v).lower() in ("n", "no", "False", "false", "f", "0"):
  	return False
  else:
  	return None


 ##################################################################33

"""

Group and Profile dataclasses

"""


@dataclass
class Group():

	group: int
	frames: int
	wait_time: int
	wait_unit: str
	run_time: int
	run_unit: str
	wait_pause: bool
	run_pause: bool
	wait_pulses: list
	run_pulses: list

	def __post_init__(self):

		self.wait_time_s = self.wait_time*to_seconds(self.wait_unit)
		self.run_time_s = self.run_time* to_seconds(self.run_unit)
		self.group_duration = (self.wait_time_s+self.run_time_s)*self.frames


@dataclass
class Profile():
	
	profile: int
	cycles: int
	duration: float
	group: dict
	total_frames: int
	n_groups: int
	wait_matrix: np.ndarray
	run_matrix: np.ndarray
	profile_frame: pd.DataFrame()

	def __post_init__(self):

		self.veto_trigger_time, self.veto_signal, self.active_out = self.build_veto_signal()


	time_units = {"ns": 1e-9, "nsec": 1e-9, "usec": 1e-6, "ms": 1e-3, "msec": 1e-3,
		"s": 1, "sec": 1, "min": 60, "m": 60, "hour": 60*60, "h": 60*60 }

	def add_group(self, Group):

		self.n_groups = self.n_groups+1
		self.total_frames = self.total_frames+Group.frames


	def build_veto_signal(self):

		trigger_time = [0]
		veto_signal = [0] #starts low and ends low
		current_time = 0 

		profile_wait_matrix = self.wait_matrix
		profile_run_matrix = self.run_matrix

		active_matrix = profile_wait_matrix+profile_run_matrix
		active_out = np.where((np.sum(active_matrix,axis=0)) != 0)[0]

		active_wait_matrix = profile_wait_matrix[:,active_out]
		active_run_matrix = profile_run_matrix[:,active_out]


		for g in range(self.n_groups):
			group = self.group[g]

			group.group_duration

			veto_active = np.sum(profile_run_matrix[g,:])

			for f in range(group.frames):

				###wait phase

				current_time += group.wait_time*to_seconds(group.wait_unit)
				trigger_time.append(current_time)
				veto_signal.append(0)
 
				#run phase

				current_time += group.run_time*to_seconds(group.run_unit)
				trigger_time.append(current_time)
				
				if veto_active != 0:
					veto_signal.append(1)
				else:
					veto_signal.append(0)


		trigger_time.append(current_time+(current_time)/10)
		veto_signal.append(0)  #starts low and ends low

		self.trigger_time = np.asarray(trigger_time)
		self.veto_signal = np.asarray(veto_signal)
		self.active_out = active_out

		return np.asarray(trigger_time), np.asarray(veto_signal), active_out

	def build_usr_signal(self,usr):

		trigger_time = [-1*self.time_units[self.best_time_unit]]
		usr_signal = [0] #starts low and ends low

		trigger_time.append(0)
		usr_signal.append(0) #starts low and ends low
		current_time = 0 

		for g in range(self.n_groups):
			group = self.group[g]

			usr_run_active = group.run_pulses[usr]
			usr_wait_active = group.wait_pulses[usr]
			usr_active = usr_run_active+usr_wait_active

			for f in range(group.frames):

				###wait phase

				current_time += group.wait_time*to_seconds(group.wait_unit)
				trigger_time.append(current_time)

				if (usr_active!=0):
					usr_signal.append(1)
				else:
					usr_signal.append(0)
 
				#run phase

				current_time += group.run_time*to_seconds(group.run_unit)
				trigger_time.append(current_time)
				
				if usr_run_active != 0:
					usr_signal.append(1)
				else:
					usr_signal.append(0)

		trigger_time.append(current_time+(current_time)/10)
		usr_signal.append(0)  #starts low and ends low

		self.trigger_time = np.asarray(trigger_time)
		self.usr_signal = np.asarray(usr_signal)

		return np.asarray(trigger_time), np.asarray(usr_signal)


	def plot_triggering(self,blocking=True):


		self.veto_trigger_time, self.veto_signal, self.active_out = self.build_veto_signal()

		close_list = [np.abs(1-np.log10(np.amin((np.asarray(self.veto_trigger_time[self.veto_trigger_time!=0])/self.time_units[i])))) for i in self.time_units.keys()]
		self.best_time_unit = list(self.time_units)[np.argmin(close_list)]
		
		print("plotting in:", self.best_time_unit)

		figure, axes = plt.subplots(len(self.active_out)+1, 1,sharex=True,figsize=(10,len(self.active_out)*4))

		if len(self.active_out) > 0:

			axes[0].step(self.veto_trigger_time/self.time_units[self.best_time_unit],self.veto_signal)
			axes[0].set_ylabel("Veto Signal")

			print(self.active_out)

			for u in range(len(self.active_out)):
				usr_trigger_time, usr_signal = self.build_usr_signal(u)
				axes[u+1].step(usr_trigger_time/self.time_units[self.best_time_unit],usr_signal)
				axes[u+1].set_ylabel(f"Usr{u} Signal")
				
			plt.xlabel(f"Time ({self.best_time_unit})")
			plt.show(block=blocking)

		else:

			print("None active in this profile")




##################################################################

class EntryPopup(ttk.Entry):
    def __init__(self, parent, iid, column, text, **kw):
        super().__init__(parent, **kw)
        self.tv = parent.tree  # reference to parent window's treeview
        self.iid = iid  # row id
        self.column = column 

        self.insert(0, text) 
        self['exportselection'] = False  # Prevents selected text from being copied to  
                                         # clipboard when widget loses focus
        self.focus_force()  # Set focus to the Entry widget
        self.select_all()   # Highlight all text within the entry widget
        self.bind("<Return>", self.on_return) # Enter key bind
        self.bind("<Control-a>", self.select_all) # CTRL + A key bind
        self.bind("<Escape>", lambda *ignore: self.destroy()) # ESC key bind
        
    def on_return(self, event):
        '''Insert text into treeview, and delete the entry popup'''
        rowid = self.tv.focus()  # Find row id of the cell which was clicked
        vals = self.tv.item(rowid, 'values')  # Returns a tuple of all values from the row with id, "rowid"
        vals = list(vals)  # Convert the values to a list so it becomes mutable
        vals[self.column] = self.get()  # Update values with the new text from the entry widget
        self.tv.item(rowid, values=vals)  # Update the Treeview cell with updated row values
        self.destroy()  # Destroy the Entry Widget
        
    def select_all(self, *ignore):
        ''' Set selection on the whole text '''
        self.selection_range(0, 'end')
        return 'break' # returns 'break' to interrupt default key-bindings

############################################################################################

class Tableview(ttk.Treeview):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tv.bind("<Double-1>", lambda event: self.onDoubleClick(event))

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

        # handle exception when header is double click
        if not rowid:
            return

        # get column position info
        x,y,width,height = self.bbox(rowid, column)

        # y-axis offset
        pady = height // 2

        # place Entry popup properly
        text = self.item(rowid, 'values')[int(column[1:])-1]
        self.entryPopup = EntryPopup(self, rowid, int(column[1:])-1, text)
        self.entryPopup.place(x=x, y=y+pady, width=width, height=height, anchor='w')

class profile_tab():

	def get_start_value(self):
		
		self.selected_start_trigger = self.clicked_start_trigger.get()
		
		return self.selected_start_trigger

	def get_n_cycles_value(self):
		
		self.selected_n_cycles = self.n_cycles_entry_value.get()
		
		return self.selected_n_cycles


	def get_inhinit_value(self):

		self.selected_external_inhibit = self.external_inhibit.get()

		return self.selected_external_inhibit

	def create_in_out_trigger(self):

		ins, outs = [], []

		for f in self.start_label_list:
			if "\u2191" in f:
				ins.append(f)
			elif "\u2193" in f:
				outs.append(f)

		return ins, outs

	def delete_profile(self):

		answer = tk.messagebox.askyesno("Close Profile", "Delete this profile? Are you sure?") 

		if answer:
			self.master.forget("current")
			# self.tab.destroy()

		return None

		# 	if self.notebook.select() == self.notebook.tabs()[-1]:
		# 		index = len(self.notebook.tabs())-1

		# 		for item in self.notebook.winfo_children():
		# 			if str(item)==index.select():
		# 				item.destroy()

		# 	return None




	def __init__(self, master, profile):

		self.master = master


		self.Columns = ["Groups","Frames","Wait Time", "Wait Units", "Run Time", "Run Units", "Wait Pause", "Run Pause", "Wait Pulses", "Run Pulses"]

		self.start_label_list = ["Software", "\u2191 BM Trigger", "\u2191 ADC chan 0", "\u2191 ADC chan 1",
		"\u2191 ADC chan 2", "\u2191 ADC chan 3", "\u2191 ADC chan 4", "\u2191 ADC chan 5", "\u2191 TTL trig 0",
		"\u2191 TTL trig 1", "\u2191 TTL trig 2", "\u2191 TTL trig 3", "\u2191 LVDS Lemo ", "\u2191 TFG cable 1",
		"\u2191 TFG cable 2", "\u2191 TFG cable 3", "\u2191 Var thrshld", "\u2193 BM Trigger",
		"\u2193 ADC chan 0", "\u2193 ADC chan 1", "\u2193 ADC chan 2", "\u2193 ADC chan 3", "\u2193 ADC chan 4",
		"\u2193 ADC chan 5", "\u2193 TTL trig 0", "\u2193 TTL trig 1", "\u2193 TTL trig 2", "\u2193 TTL trig 3",
		"\u2193 LVDS Lemo", "\u2193 TFG cable 1", "\u2193 TFG cable 2", "\u2193 TFG cable 3",
		"\u2193 Var thrshld"]


		self.display_pause = ["Software", "No Pause", "\u2191 BM Trigger", "\u2191 ADC chan 0",
		"\u2191 ADC chan 1", "\u2191 ADC chan 2", "\u2191 ADC chan 3", "\u2191 ADC chan 4", "\u2191 ADC chan 5",
		"\u2191 TTL trig 0", "\u2191 TTL trig 1", "\u2191 TTL trig 2", "\u2191 TTL trig 3", "\u2191 LVDS Lemo ",
		"\u2191 TFG cable 1", "\u2191 TFG cable 2", "\u2191 TFG cable 3", "\u2191 Var thrshld",
		"\u2193 BM Trigger", "\u2193 ADC chan 0", "\u2193 ADC chan 1", "\u2193 ADC chan 2", "\u2193 ADC chan 3",
		"\u2193 ADC chan 4", "\u2193 ADC chan 5", "\u2193 TTL trig 0", "\u2193 TTL trig 1", "\u2193 TTL trig 2",
		"\u2193 TTL trig 3", "\u2193 LVDS Lemo", "\u2193 TFG cable 1", "\u2193 TFG cable 2", "\u2193 TFG cable 3",
		"\u2193 Var thrshld"]

		self.output_trigger_labels = ["Output1", "Output2", "Output3", "Output4", "Output5", "Output6",
		"Output7", "Output8"]

		self.ins, self.outs = self.create_in_out_trigger()


		self.tab = ttk.Frame(self.master,borderwidth=5, relief='raised') 
		frame = self.master.add(self.tab, text ='Profile '+str(profile.profile+1)) 
		
		### add tree view ############################################
		self.profile_config_tree = ttk.Treeview(self.tab, columns=self.Columns, show="headings")
		#add the columns headers
		for i, col in enumerate(self.Columns):
			self.profile_config_tree.heading(i, text=col)
			self.profile_config_tree.column(i, width=150, stretch=True)

		profile_table = profile.profile_frame
		profile_table = profile_table.reset_index()

		# Insert sample data into the Treeview
		for i in range(len(profile_table)):
			self.profile_config_tree.insert("", "end", values=list(profile_table.iloc[i]))
		self.profile_config_tree.grid(column = 0, row = 5,padx = 5,pady = 5,columnspan=len(self.Columns),rowspan=len(profile_table))
		self.profile_config_tree.bind("<Double-1>", lambda event: self.onDoubleClick(event))

		############################################################

		##### input trigger select

		input_trigger_label = ttk.Label(self.tab, text ="Start method")
		input_trigger_label.grid(column = 0, row = 0, padx = 5,pady = 5 ,sticky="e" )
		
		self.clicked_start_trigger = tk.StringVar() 
		starttrigger_dropdown = ttk.OptionMenu(self.tab , self.clicked_start_trigger , self.start_label_list[0]) 
		starttrigger_dropdown.grid(column =1, row = 0, padx = 5,pady = 5 ,sticky="w" )
		menu = starttrigger_dropdown["menu"]


		software_sublist = tk.Menu(menu, tearoff=False)
		menu.add_cascade(label="software", menu=software_sublist)
		software_sublist.add_command(label = "software", command = lambda:self.clicked_start_trigger.set(in_trig))


		ins_sublist = tk.Menu(menu, tearoff=False)
		menu.add_cascade(label="ins", menu=ins_sublist)
		for in_trig in self.ins:
			# sublist.add_command(label = in_trig, command = lambda:self.clicked_start_trigge.set())
			ins_sublist.add_command(label = in_trig, command = lambda:self.clicked_start_trigger.set(in_trig))


		outs_sublist = tk.Menu(menu, tearoff=False)
		menu.add_cascade(label="outs", menu=outs_sublist)
		for out_trig in self.outs:
			# sublist.add_command(label = in_trig, command = lambda:self.clicked_start_trigge.set())
			outs_sublist.add_command(label = out_trig, command = lambda:self.clicked_start_trigger.set(out_trig))

		
		##### output trigger select

		output_trigger_label = ttk.Label(self.tab, text ="Output Trigger").grid(column = 0, row = 2, padx = 5,pady = 5 ,sticky="e" )
		clicked_output_trigger = tk.StringVar() 
		output_rigger_dropdown = ttk.OptionMenu(self.tab , clicked_output_trigger , self.output_trigger_labels[0], *self.output_trigger_labels,) 
		output_rigger_dropdown.grid(column = 1, row = 2,padx = 5,pady = 5,sticky="w" )
		self.selected_output_trigger = clicked_output_trigger.get()

		################# external inhibit select

		self.external_inhibit = tk.IntVar() 
		external_inhibit_button = tk.Checkbutton(self.tab, text = "External Inhibit", 
						variable = self.external_inhibit, 
						onvalue = 1, 
						offvalue = 0, 
						height = 2, 
						width = 20) 
		external_inhibit_button.grid(column = 2, row = 0, padx = 5,pady = 5 ,sticky="w" )

		############# number of cycles box

		############# number of cycles box

		n_cycles_label = tk.Label(self.tab, text="No. of cycles").grid(column = 3, row = 0, padx = 5,pady = 5 ,sticky="e" )
		self.n_cycles_entry_value = tk.IntVar(self.tab, value=profile.cycles)
		n_cycles_entry = tk.Entry(self.tab, bd =1, textvariable=self.n_cycles_entry_value)
		n_cycles_entry.grid(column = 4, row = 0, padx = 5,pady = 5 ,sticky="w" )

		############# plot button

		self.plot_profile_button = tk.Button(self.tab, text ="Plot Profile", command = profile.plot_triggering).grid(column = 8, row = 0, padx = 5,pady = 5,columnspan=1, sticky='e')

		############# profile info

		#### total frames
		total_frames_label = tk.Label(self.tab, text=f"Total Frames: {profile.total_frames}").grid(column = 8, row = 1, padx = 5,pady = 5 ,sticky="e" )

		### total time
		total_time_label = tk.Label(self.tab, text=f"Total time: {np.amax(profile.veto_trigger_time):.3f} s").grid(column = 8, row = 2, padx = 5,pady = 5 ,sticky="e" )


		############profile settings
		
		self.insertrow_button = tk.Button(self.tab, text ="Insert group", command = profile.plot_triggering).grid(column = 0, row = 10, padx = 5,pady = 5,columnspan=1, sticky='w')
		self.deleterow_button = tk.Button(self.tab, text ="Delete group", command = profile.plot_triggering).grid(column = 1, row = 10, padx = 5,pady = 5,columnspan=1, sticky='w')

		self.delete_profile_button = tk.Button(self.tab, text ="Delete Profile", command = self.delete_profile).grid(column = 9, row = 10, padx = 5,pady = 5,columnspan=1, sticky='e')


class panda_config_builder(tk.Tk):

	def theme(self, theme_name):

		style = ttk.Style(self.window)

		self.theme_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),"themes",theme_name+'.tcl')

		self.window.tk.eval(self.theme_dir)
		# tell tcl where to find the awthemes packages
		# self.window.tk.eval("""
		# set base_theme_dir /path/to/downloaded/theme/awthemes-9.2.2/

		# package ifneeded awthemes 9.2.2 \
		#     [list source [file join $base_theme_dir awthemes.tcl]]
		# package ifneeded colorutils 4.8 \
		#     [list source [file join $base_theme_dir colorutils.tcl]]
		# package ifneeded awdark 7.7 \
		#     [list source [file join $base_theme_dir awdark.tcl]]
		# package ifneeded awlight 7.6 \
		#     [list source [file join $base_theme_dir awlight.tcl]]
		# """)
		# load the awdark and awlight themes
		self.window.tk.call("package", "require", theme_name)
		# self.window.tk.call("package", "require", 'awlight')

		print(style.theme_names())
		# --> ('awlight', 'clam', 'alt', 'default', 'awdark', 'classic')

		style.theme_use(theme_name)

	def calculate(self, *args):
		try:
			value = float(self.feet.get())
			self.meters.set(int(0.3048 * value * 10000.0 + 0.5)/10000.0)
		except ValueError:
			pass

	def add_profile(self, event):

		if self.notebook.select() == self.notebook.tabs()[-1]:

			self.notebook.forget(self.add_frame)

			n_profile_tab = profile_tab(self.notebook, self.profile_dict[0]).tab

			# default_configuration = configure_trigger(self.default_config_path)

			# profile = default_configuration.profile_dict[0]
			# new_profile_tab = profile_tab(self.notebook, profile)

			self.profile_tabs[len(self.profile_tabs)] = n_profile_tab
			self.notebook.add(n_profile_tab, text="Profile " + str(len(self.profile_tabs)))

			self.add_frame = tk.Frame()
			self.notebook.add(self.add_frame, text="+")
			self.window.bind("<<NotebookTabChanged>>", self.add_profile)


			# default_configuration = configure_trigger(self.default_config_path)

			# profile = default_configuration.profile_dict[0]
			# new_profile_tab = profile_tab(self.notebook, profile)

			# self.notebook.forget(self.add_frame)

			# self.profile_tabs[len(self.profile_tabs)] = n_profile_tab
			# self.notebook.add(new_profile_tab, text="Profile" + str(len(self.profile_tabs)))

			# self.add_frame = tk.Frame()
			# self.notebook.add(self.add_frame, text="+")
			# self.window.bind("<<NotebookTabChanged>>", self.add_profile)


	# def delete_profile(self):

	# 	if self.notebook.select() == self.notebook.tabs()[-1]:
	# 		index = len(self.notebook.tabs())-1

	# 		for item in self.notebook.winfo_children():
	# 			if str(item)==index.select():
	# 				item.destroy()

	# 	return None




	def load_config(self):
		panda_config_yaml = fd.askopenfilename()

		answer = tk.messagebox.askyesno("Close/Open New", "Finished editing this profile? Continue?") 

		if answer:
			self.window.destroy()
			panda_config_builder(panda_config_yaml)
		else:
			return

	def save_config(self):

		print("save this experiment")


	def show_start_value(self):
		self.selected_start_trigger = self.clicked_start_trigger.get()
		print(self.selected_start_trigger)


	def __init__(self,panda_config_yaml=None):


		self.panda_config_yaml = panda_config_yaml
		self.default_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"default_panda_config.yaml")
		
		if self.panda_config_yaml == None:
			configuration = configure_trigger(self.default_config_path)
		else:
			configuration = configure_trigger(panda_config_yaml)

		self.profile_dict = configuration.profile_dict
		self.n_profiles = len(self.profile_dict)
		self.window = tk.Tk()

		self.window.resizable(0,0)
		# self.window.geometry('2030x600')
		self.window.title("Panda Config") 
		self.notebook = ttk.Notebook(self.window)
		self.notebook.pack(fill ="both",expand=False)

		self.profile_tabs = {}

		for i in range(self.n_profiles):

			n_profile_tab = profile_tab(self.notebook, self.profile_dict[i])

			self.profile_tabs[i] = n_profile_tab

		######## #settings and buttons that apply to all profiles

		self.global_settings_frame = ttk.Frame(self.window,borderwidth=5, relief='raised')
		self.global_settings_frame.pack(fill ="both",expand=True)

		#add a load/save/configure button
		self.load_button = tk.Button(self.global_settings_frame, text ="Load", command = self.load_config).grid(column = 1, row = 0, padx = 5,pady = 5,columnspan=1)
		self.save_button = tk.Button(self.global_settings_frame, text ="Save", command = self.save_config).grid(column = 2, row = 0, padx = 5,pady = 5,columnspan=1)
		self.configure_button = tk.Button(self.global_settings_frame, text ="Configure", command = self.show_start_value).grid(column = 3, row = 0, padx = 5,pady = 5,columnspan=1)

		# # add a scrollbar
		# scrollbar = ttk.Scrollbar(window, orient=tk.VERTICAL, command=profile_config_tree.yview)
		# tree.configure(yscroll=scrollbar.set)
		# scrollbar.grid(row=0, column=1, sticky='ns')

		#allow adding of new profile tabs

		# self.notebook.add(n_profile_tab, text="Profile" + len(self.profile_tabs))
		# self.window.bind("<<NotebookTabChanged>>", self.add_profile)
		
		# self.window.bind("<<NotebookTabChanged>>", self.add_profile)


		self.add_frame = tk.Frame()
		self.notebook.add(self.add_frame, text="+")
		self.window.bind("<<NotebookTabChanged>>", self.add_profile)

		#########################################
		#go

		# self.window.columnconfigure(0, weight=1)
		# self.window.rowconfigure(0, weight=1)
		# try:
		# 	import sv_ttk
		# 	sv_ttk.set_theme("light")
		# 	toggle_button = ttk.Button(self.global_settings_frame, text="Dark/light mode", command=sv_ttk.toggle_theme)
		# 	toggle_button.grid(column = 10, row = 0, padx = 5,pady = 5,columnspan=1, sticky='e')
		# except:
		# 	pass

		self.window.mainloop()


class configure_trigger():


	def build_config(self):

		panda_config_builder()
		print("Build a .yaml to configure the pandas trigger")



	def read_legacy_config_yaml(self):

		with open(self.config_filepath, 'rb') as file:
			print("Using config:",self.config_filepath)

			self.config = yaml.full_load(file)

			print(self.config["Experiment"]["Timing"]["Profile"])
			print(self.config["Experiment"]["Timing"]["Profile"][0])


	def convert_properties_to_dict(self, profile):

		profile_properties_text = profile.text
		prof_prop_list = (profile_properties_text.replace('\n','')).split(',')
		prof_prop_list[0] = profile.tag+"="+str(prof_prop_list[0])
		prof_prop_list = [f.split('=') for f in prof_prop_list]
		prof_prop_dict = dict(prof_prop_list)

		return prof_prop_dict


	def read_gda_config(self):

		tree = ET.parse(self.config_filepath)
		xmlroot = tree.getroot()

		for experiment in xmlroot:
			# print(experiment.tag, experiment.attrib)

			for n,profile in enumerate(experiment):

				profile_properties = self.convert_properties_to_dict(profile)
				
				print(profile_properties)
				print(profile.tag, (profile.text) ) 
				quit()

				for element in profile:
			  		
					print(element.tag, element.attrib)

					if element.tag == "Frames":
						print(element.text)
					if element.tag == "OutputTrigger":

						print(element.text)
						
						for subelement in element:
							print(subelement.tag)






	def read_config(self, config_filepath):

		with open(config_filepath, 'rb') as file:
			print("Using config:",config_filepath)

			if config_filepath.endswith('.yaml') or config_filepath.endswith('.yml'):
				self.config = yaml.full_load(file)
			else:
				print("Must be .yaml/.yml file")
				quit()

			# print(self.config)
		
			self.instrument = self.config["setup"]["instrument"]
			self.experiment = self.config["setup"]["experiment"]
			self.user = self.config["setup"]["user"]

			if "year" not in self.config:
				self.year = datetime.now().year
			else:
				self.year = self.config["setup"]["year"]


			self.data_dir = os.path.join("/dls",self.instrument,"data",str(self.year),self.experiment)

			print(self.user)
			print(self.experiment)
			print(self.data_dir)

			profile_names = [f for f in self.config if f.startswith("profile")]

			self.profile_dict = {}

			for p,profile_name in enumerate(profile_names):

				profile_cycles = self.config[profile_name]["cycles"]
				groups = {key: self.config[profile_name][key] for key in self.config[profile_name].keys() if key.startswith("group")}
				profile_duration = 0
				profile_total_frames = 0
				profile_frame = pd.DataFrame(groups).transpose()

				group_dict = {}

				wait_matrix = []
				run_matrix = []

				for g,group_name in enumerate(groups.keys()):

					group = self.config[profile_name][group_name]

					n_Group  = Group(g, group["frames"], group["wait_time"], group["wait_units"], group["run_time"], group["run_units"],
						group["wait_pause"], group["run_pause"], group["wait_pulses"], group["run_pulses"])

					profile_duration+=n_Group.group_duration
					profile_total_frames+=n_Group.frames

					group_dict[g] = n_Group

					wait_matrix.append(n_Group.wait_pulses)
					run_matrix.append(n_Group.run_pulses)

				wait_matrix = np.asarray(wait_matrix)
				run_matrix = np.asarray(run_matrix)

				n_profile = Profile(p, profile_cycles, profile_duration, group_dict, profile_total_frames, len(group_dict), wait_matrix, run_matrix, profile_frame)
				print(n_profile)


				# print(n_profile.plot_triggering())

				self.profile_dict[p] = n_profile



	def __init__(self,config_filepath=None):


		self.config_filepath = config_filepath

		# if self.config_filepath.endswith('.yaml'):
		# 	self.read_legacy_config_yaml()

		if self.config_filepath.endswith('.xml'):
			self.read_gda_config(self.config_filepath)
		elif self.config_filepath.endswith('.yaml') or self.config_filepath.endswith('.yml'):
			self.read_config(self.config_filepath)
		else:
			self.build_config()










if __name__ == '__main__':

	gda_config_filepath = '/scratch/i22/panda_config.xml'

	# print(3, decimal_to_binary(3))
	# print(192, decimal_to_binary(192))
	# quit()

	dir_path = os.path.dirname(os.path.realpath(__file__))

	print(dir_path)


	converted_config_filepath = '/scratch/i22/panda_config_original.yaml'

	config_filepath = os.path.join(dir_path,"panda_config.yaml")
	panda_config_builder(config_filepath)
	# quit()


	panda_trigger = configure_trigger(config_filepath)
	# panda_trigger.plot_triggering(1,confirm=True)

