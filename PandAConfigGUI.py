#!/dls/science/users/akz63626/i22/i22_venv/bin/python


"""

Python dataclasses and GUI as a replacement for NCDDetectors

"""

import os
import yaml
import matplotlib.pyplot as plt
from pathlib import Path
from importlib import import_module

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd

from dodal.utils import get_beamline_name

from dodal.beamlines.i22 import panda1

from blueapi.client.event_bus import EventBusClient
from bluesky_stomp.messaging import StompClient, BasicAuthentication
from blueapi.client.client import BlueapiRestClient, BlueapiClient
from blueapi.config import RestConfig, ConfigLoader, ApplicationConfig
from stomp import Connection

from ProfileGroups import Profile, Group, PandaTriggerConfig

from PandAGUIElements import ProfileTab
from stubs.PandAStubs import return_connected_device


__version__ = '0.2'
__author__ = 'Richard Dixey'

############################################################################################

BL = get_beamline_name(os.environ['BEAMLINE'])
BL_config = import_module(f"beamline_configs.{BL}_config")

THEME_NAME = BL_config.THEME_NAME
PULSEBLOCKS = BL_config.PULSEBLOCKS
THEME_NAME = BL_config.THEME_NAME

TTLIN = BL_config.TTLIN
TTLOUT = BL_config.TTLOUT
LVDSIN = BL_config.LVDSIN
LVDSOUT = BL_config.LVDSOUT

PULSE_CONNECTIONS = BL_config.PULSE_CONNECTIONS

############################################################################################


class PandaConfigBuilderGUI(tk.Tk):

	def theme(self, theme_name):

		style = ttk.Style(self.window)

		print(style.theme_names())

		style.theme_use(THEME_NAME)

		self.theme_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),"themes",theme_name+'.tcl')

		# self.window.tk.eval(self.theme_dir)
		# self.window.tk.call("package", "require", theme_name)

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
			self.client.run_plan("setup_panda")
		except:
			print("could not upload yaml to panda")

		try:
			self.client.run_plan("setup_panda")
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

		for key in TTLIN.keys():
			INDev = TTLIN[key]

			ax.scatter(0, key, color='k',s=50)
			ax.text(0+0.1, key, INDev)

		for key in LVDSIN.keys():
			LVDSINDev = LVDSIN[key]

			ax.scatter(1, key, color='k',s=50)
			ax.text(1+0.1, key, LVDSINDev)

		for key in TTLOUT.keys():
			TTLOUTDev = TTLOUT[key]

			ax.scatter(2, key, color='b',s=50)
			ax.text(2+0.1, key, TTLOUTDev)

		for key in LVDSOUT.keys():
			LVDSOUTDev = LVDSOUT[key]
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

	def run_plan(self):

		current_profile = self.notebook.index("current")

		profile = self.configuration.profiles[current_profile]
		json_schema_profile = profile.model_dump_json()
		print(json_schema_profile)

		experiment = "cm40643-3"

		command = f"run_panda_triggering(experiment={experiment},profile={json_schema_profile}))"

		print(self.client.run_task(command))

	def build_exp_run_frame(self):
		
		self.run_frame = ttk.Frame(self.window,borderwidth=5, relief='raised')
		self.run_frame.pack(fill ="both",expand=True, side="right")
		self.get_plans_button = ttk.Button(self.run_frame, text ="Get Plans", command = self.get_plans).grid(column = 2, row = 1, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.get_devices_button = ttk.Button(self.run_frame, text ="Get Devices", command = self.get_devices).grid(column = 2, row = 3, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.stop_plans_button = ttk.Button(self.run_frame, text ="Stop Plan", command = self.stop_plans).grid(column = 2, row = 5, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.pause_plans_button = ttk.Button(self.run_frame, text ="Pause Plan", command = self.pause_plans).grid(column = 2, row = 7, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.resume_plans_button = ttk.Button(self.run_frame, text ="Resume Plan", command = self.resume_plans).grid(column = 2, row = 9, padx = 5,pady = 5,columnspan=1, sticky='news')
		self.run_plan_button = ttk.Button(self.run_frame, text ="Run Plan", command = self.run_plan).grid(column = 2, row = 11, padx = 5,pady = 5,columnspan=1, sticky='news')

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

			for n, det in enumerate(PULSE_CONNECTIONS[pulse+1]):

				experiment_var = tk.StringVar(value=self.configuration.experiment)

				if (det.lower() == "fs") or ("shutter" in det.lower()):
					ad_entry = tk.Checkbutton(active_detectors_frame_n, bd =1, text=det, state='disabled')
					ad_entry.select()
				else:
					ad_entry = tk.Checkbutton(active_detectors_frame_n, bd =1, text=det)

				ad_entry.grid(column = n+1, row = 1, padx = 5,pady = 5 ,sticky="w" )

	def build_pulse_frame(self):

		self.pulse_frame = ttk.Frame(self.window, borderwidth=5, relief='raised')
		self.pulse_frame.pack(fill ="both",side='left',expand=True)
		Outlabel = ttk.Label(self.pulse_frame, text =f"Enable Device")
		Outlabel.pack(fill ="both",side='top',expand=True)


	def __init__(self,panda_config_yaml=None):

		if os.environ.get('USER') != "akz63626": #check if I am runing this

			try:
				self.panda = return_connected_device(BL, "panda1")
			except:
				answer = tk.messagebox.askyesno("PandA not Connected", "PandA is not connected, if you continue things will not work. Continue?")
				if answer:
					pass
				else:
					quit()


		self.panda_config_yaml = panda_config_yaml
		self.default_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"profile_yamls","default_panda_config.yaml")
		
		if self.panda_config_yaml == None:
			self.configuration = PandaTriggerConfig.read_from_yaml(self.default_config_path)
		else:
			self.configuration = PandaTriggerConfig.read_from_yaml(self.panda_config_yaml)

		
		if self.configuration.experiment == None:
			user_input = tk.simpledialog.askstring(title="Experiment",
                                  prompt="Enter an experiment code:")
			
			self.configuration.experiment = user_input


		self.profiles = self.configuration.profiles

		self.window = tk.Tk()
		self.window.resizable(1,1)
		self.window.minsize(600,200)
		self.theme("alt")

		
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

		#option 1 - but doesn't work


		# self.config = RestConfig(host=f"{BL}-blueapi.diamond.ac.uk", port=443, protocol="https")
		# self.rest_client = BlueapiRestClient(self.config)

		# self.stomp_connection = Connection([(f"{BL}-rabbitmq-daq.diamond.ac.uk",443)])
		# self.stomp_connection.connect(BL, BL[::-1], wait=True)
		# self.authentication = BasicAuthentication(username=BL, password=BL[::-1])
		# self.event_bus = EventBusClient(StompClient(conn=self.stomp_connection, authentication=self.authentication))
		# self.client = BlueapiClient(rest=self.rest_client, events=self.events_bus)


		#option 2 - but doesn't work with tasks creation/running plans etc

		# self.config = RestConfig(host=f"{BL}-blueapi.diamond.ac.uk", port=443, protocol="https")
		# self.rest_client = BlueapiRestClient(self.config)
		# self.client = BlueapiClient(rest=self.rest_client, events=self.events_bus)


		#option 3 - return bad request error when trying to run a plan

		blueapi_config_path = Path(os.path.join(os.path.dirname(os.path.realpath(__file__)),f"{BL}_blueapi_config.yaml"))
		config_loader = ConfigLoader(ApplicationConfig)
		config_loader.use_values_from_yaml(blueapi_config_path)
		loaded_config = config_loader.load()
		self.client = BlueapiClient.from_config(loaded_config)



		self.window.mainloop()




if __name__ == '__main__':

	#https://github.com/DiamondLightSource/blueapi/blob/main/src/blueapi/client/client.py <- use this to do stuff

	# blueapi -c i22_blueapi_config.yaml controller run count '{"detectors":["saxs"]}'


	dir_path = os.path.dirname(os.path.realpath(__file__))
	print(dir_path)
	config_filepath = os.path.join(dir_path,"profile_yamls","panda_config.yaml")
	PandaConfigBuilderGUI(config_filepath)

