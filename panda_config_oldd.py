import numpy as np
np.seterr(divide='ignore', invalid='ignore') #dividing by zero throws a warning, this is expected due to some pixels being dead
import argparse, os
import pandas as pd
import yaml
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import matplotlib.pyplot as plt

import xml.etree.ElementTree as ET

import time

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


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


############################################################################################




class panda_config_builder():

	def calculate(self, *args):
		try:
			value = float(self.feet.get())
			self.meters.set(int(0.3048 * value * 10000.0 + 0.5)/10000.0)
		except ValueError:
			pass

	def AddProfile(self, event):
		if self.notebook.select() == self.notebook.tabs()[-1]:
			index = len(self.notebook.tabs())-1
			frame = tk.Frame(self.notebook)
			self.notebook.insert(index, frame, text= "Profile " + str(len(self.notebook.tabs())))
			self.notebook.select(index)

	def refresh(self):
		self.window.destroy()
		self.__init__()


	def load_config(self):
		panda_config_yaml = fd.askopenfilename()

		answer = messagebox.askyesno("Close/Open New", "Finished editing this profile? Continue?") 

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

	def profile_tab(self, notebook, profile):

		tab = ttk.Frame(self.notebook,borderwidth=5, relief='raised') 
		frame = self.notebook.add(tab, text ='Profile '+str(profile.profile+1)) 
		
		profile_label = ttk.Label(tab, text ="Profile"+str(profile.profile+1)).grid(column = 0, row = 0, padx = 30,pady = 30,columnspan=len(self.Columns))
		# self.notebook.pack(expand = 1, fill ="both")
		
		# # Insert sample data into the Treeview
		# for i in range(len(profile)):

		# 	for n,col in enumerate(profile.columns):
		# 		row_col_entry = tk.Entry(tab,textvariable = col, font=('calibre',10,'normal'))
		# 		row_col_entry.insert(0, profile.iloc[i][col]) 
		# 		row_col_entry.grid(row=i,column=n)


		profile_config_tree = ttk.Treeview(tab, columns=self.Columns, show="headings")
		#add the columns headers
		for col in self.Columns:
			profile_config_tree.heading(col, text=col)

		profile_table = profile.profile_frame
		profile_table = profile_table.reset_index()

		# Insert sample data into the Treeview
		for i in range(len(profile_table)):
			profile_config_tree.insert("", "end", values=list(profile_table.iloc[i]))
		profile_config_tree.grid(column = 0, row = 5,padx = 5,pady = 5,columnspan=len(self.Columns),rowspan=len(profile_table))


		# start_trigger_label = ttk.Label(tab, text ="Start Trigger")
		# start_trigger_label.grid(column = 0, row = 0, padx = 5,pady = 5 ,sticky="e" )
		# self.clicked_start_trigger = tk.StringVar() 
		# starttrigger_dropdown = ttk.OptionMenu(tab , self.clicked_start_trigger , self.start_label_list[0], *self.start_label_list,) 
		# starttrigger_dropdown.grid(column = 1, row = 0,padx = 5,pady = 5,sticky="w" )
		# self.selected_start_trigger = self.clicked_start_trigger.get()

		##### input trigger select

		input_trigger_label = ttk.Label(tab, text ="Start method")
		input_trigger_label.grid(column = 0, row = 0, padx = 5,pady = 5 ,sticky="e" )
		
		self.clicked_start_trigger = tk.StringVar() 
		starttrigger_dropdown = ttk.OptionMenu(tab , self.clicked_start_trigger , self.start_label_list[0]) 
		starttrigger_dropdown.grid(column =1, row = 0, padx = 5,pady = 5 ,sticky="w" )
		menu = starttrigger_dropdown["menu"]


		software_sublist = tk.Menu(menu, tearoff=False)
		menu.add_cascade(label="software", menu=software_sublist)
		software_sublist.add_command(label = "software", command = lambda:self.clicked_start_trigger.set(self.start_label_list[0]))


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

		output_trigger_label = ttk.Label(tab, text ="Output Trigger").grid(column = 0, row = 2, padx = 5,pady = 5 ,sticky="e" )
		clicked_output_trigger = tk.StringVar() 
		output_rigger_dropdown = ttk.OptionMenu(tab , clicked_output_trigger , self.output_trigger_labels[0], *self.output_trigger_labels,) 
		output_rigger_dropdown.grid(column = 1, row = 2,padx = 5,pady = 5,sticky="w" )
		self.selected_output_trigger = clicked_output_trigger.get()

		return tab

	def create_in_out_trigger(self):

		ins, outs = [], []

		for f in self.start_label_list:
			if "\u2191" in f:
				ins.append(f)
			elif "\u2193" in f:
				outs.append(f)

		return ins, outs

	def __init__(self,panda_config_yaml=None):


		self.panda_config_yaml = panda_config_yaml
		
		if self.panda_config_yaml == None:
			configuration = configure_trigger(os.path.join(os.path.dirname(os.path.realpath(__file__)),"default_panda_config.yaml"))
		else:
			configuration = configure_trigger(panda_config_yaml)

		self.profile_dict = configuration.profile_dict
		self.n_profiles = len(self.profile_dict)

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

		# self.n_profiles = 3

		# mainframe = ttk.Frame(window, padding="3 3 12 12")
		# mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
		# window.columnconfigure(0, weight=1)
		# window.rowconfigure(0, weight=1)

		# self.feet = StringVar()
		# feet_entry = ttk.Entry(mainframe, width=7, textvariable=self.feet)
		# feet_entry.grid(column=2, row=1, sticky=(W, E))

		# self.meters = StringVar()
		# ttk.Label(mainframe, textvariable=self.meters).grid(column=2, row=2, sticky=(W, E))

		# ttk.Button(mainframe, text="Calculate", command=self.calculate).grid(column=3, row=3, sticky=W)

		# ttk.Label(mainframe, text="feet").grid(column=3, row=1, sticky=W)
		# ttk.Label(mainframe, text="is equivalent to").grid(column=1, row=2, sticky=E)
		# ttk.Label(mainframe, text="meters").grid(column=3, row=2, sticky=W)

		# for child in mainframe.winfo_children(): 
		#	 child.grid_configure(padx=5, pady=5)

		# feet_entry.focus()
		# window.bind("<Return>", self.calculate)

		# window.mainloop()

		self.window = tk.Tk()
		self.window.resizable(1,1)
		# self.window.geometry('2030x600')
		self.window.title("Panda Config") 
		self.notebook = ttk.Notebook(self.window)
		self.notebook.pack(fill ="both",expand=False)

		for i in range(self.n_profiles):

			tab = self.profile_tab(self.notebook, self.profile_dict[i])

			# ref_button = tk.Button(tab, text ="Refresh", command = self.refresh)
			# ref_button.grid(column = 0, row = 0, padx = 5,pady = 5,columnspan=1)
			# tab.grid(column = 5, row = 5, padx = 5,pady = 5,columnspan=10)


		######## #settings and buttons that apply to all profiles

		self.global_settings_frame = ttk.Frame(self.window,borderwidth=5, relief='raised')
		self.global_settings_frame.pack(fill ="both",expand=False)

		#add a load/save/configure button
		self.load_button = tk.Button(self.global_settings_frame, text ="Load", command = self.load_config).grid(column = 1, row = 0, padx = 5,pady = 5,columnspan=1)
		self.save_button = tk.Button(self.global_settings_frame, text ="Save", command = self.save_config).grid(column = 2, row = 0, padx = 5,pady = 5,columnspan=1)
		self.configure_button = tk.Button(self.global_settings_frame, text ="Configure", command = self.show_start_value).grid(column = 3, row = 0, padx = 5,pady = 5,columnspan=1)

		# # add a scrollbar
		# scrollbar = ttk.Scrollbar(window, orient=tk.VERTICAL, command=profile_config_tree.yview)
		# tree.configure(yscroll=scrollbar.set)
		# scrollbar.grid(row=0, column=1, sticky='ns')

		#allow adding of new profile tabs
		add_frame = tk.Frame()
		self.notebook.add(add_frame, text="+")
		self.window.bind("<<NotebookTabChanged>>", self.AddProfile)



	



		#########################################
		#go



		self.window.columnconfigure(0, weight=1)
		self.window.rowconfigure(0, weight=1)


		self.window.mainloop()

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
	group_duration: float


@dataclass
class Profile():
	
	profile: int
	cycles: int
	duration: float
	group: dict
	total_frames: int
	n_groups:int
	wait_matrix: np.ndarray
	run_matrix: np.ndarray
	profile_frame: pd.DataFrame()

	time_units = {"ns": 1e-9, "nsec": 1e-9, "usec": 1e-6, "ms": 1e-3, "msec": 1e-3,
		"s": 1, "sec": 1, "min": 60, "m": 60, "hour": 60*60, "h": 60*60 }

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






	def read_config(self):

		with open(self.config_filepath, 'rb') as file:
			print("Using config:",self.config_filepath)

			if self.config_filepath.endswith('.yaml') or self.config_filepath.endswith('.yml'):
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

					wait_time = group["wait_time"]* to_seconds(group["wait_units"])
					run_time = group["run_time"]* to_seconds(group["run_units"])
					group_duration = (wait_time+run_time)*group["frames"]

					profile_duration+=group_duration
					profile_total_frames+=group["frames"]


					n_Group  = Group(g, group["frames"], group["wait_time"], group["wait_units"], group["run_time"], group["run_units"],
						group["wait_pause"], group["run_pause"], group["wait_pulses"], group["run_pulses"], group_duration)

					group_dict[g] = n_Group

					wait_matrix.append(group["wait_pulses"])
					run_matrix.append(group["run_pulses"])

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
			self.read_gda_config()
		elif self.config_filepath.endswith('.yaml') or self.config_filepath.endswith('.yml'):
			self.read_config()
		else:
			self.build_config()










if __name__ == '__main__':

	gda_config_filepath = '/scratch/i22/panda_config.xml'

	# print(3, decimal_to_binary(3))
	# print(192, decimal_to_binary(192))
	# quit()

	dir_path = os.path.dirname(os.path.realpath(__file__))


	converted_config_filepath = '/scratch/i22/panda_config_original.yaml'

	config_filepath = os.path.join(dir_path,"panda_config.yaml")
	panda_config_builder(config_filepath)
	quit()


	panda_trigger = configure_trigger(gda_config_filepath)
	# panda_trigger.plot_triggering(1,confirm=True)

