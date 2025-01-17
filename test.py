import tkinter as tk
from tkinter import ttk
 
 
class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title('Test')
        self.iconbitmap()
        # self.state('zoomed')
        paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.tree_view_frame = TreeviewFrame(
            paned_window, width=75, height=300, relief=tk.SUNKEN)
        self.tree_view_frame.tree_view.bind(
            '<<TreeviewSelect>>', self.on_tree_view_select)
        self.display_frame = DisplayFrame(
            paned_window, width=400, height=300, relief=tk.SUNKEN)
        paned_window.add(self.tree_view_frame, weight=0)
        paned_window.add(self.display_frame, weight=4)
        paned_window.pack(fill=tk.BOTH, expand=True)
 
    def on_tree_view_select(self, event):
        frame_id = self.tree_view_frame.tree_view.selection()
        self.display_frame.change_frame(frame_id)
 
 
class TreeviewFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tree_view = ttk.Treeview(self)
        tree_view.pack()
        tree_view.insert('', '0', 'item1', text='PRODUCT')
 
        tree_view.insert('item1', '0', 'A', text='A')
 
        tree_view.insert('item1', '1', 'B', text='B')
        tree_view.insert('item1', '2', 'C', text='C')
        tree_view.insert('item1', '3', 'D', text='D')
        tree_view.insert('', '1', 'item2', text='REPORTS')
 
        tree_view.insert('', '3', 'item3', text='QUERIES')
        tree_view.config(height=100)
        self.tree_view = tree_view
 
 
class DisplayFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.config(bg='Red')
        self.frames = {('item1',): ProductFrame(self),
                       ('A',): AFrame(self),
                       ('B',): BFrame(self),
                       ('C',): CFrame(self),
                       ('D',): DFrame(self),
                       ('item2',): ReportsFrame(self),
                       ('item3',): QueriesFrame(self)}
 
    def change_frame(self, frame_id):
        for widget in self.winfo_children():
            widget.pack_forget()
        try:
            self.frames[frame_id].pack(fill=tk.BOTH, expand=True)
        except KeyError as error:
            print(f'Unkown frame id: {error}')
 
 
class ProductFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style = ttk.Style(self)
        style.configure('ProductFrame.TFrame', background='red')
        self.config(style='ProductFrame.TFrame')
        label = ttk.Label(self, text='ProductFrame')
        label.pack(padx=10, pady=10, anchor=tk.CENTER)
 
 
class AFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style = ttk.Style(self)
        style.configure('AFrame.TFrame', background='Blue')
        self.config(style='AFrame.TFrame')
        label = ttk.Label(self, text='AFrame')
        label.pack(padx=10, pady=10, anchor=tk.CENTER)
 
 
class BFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style = ttk.Style(self)
        style.configure('BFrame.TFrame', background='Green')
        self.config(style='BFrame.TFrame')
        label = ttk.Label(self, text='BFrame')
        label.pack(padx=10, pady=10, anchor=tk.CENTER)
 
 
class CFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style = ttk.Style(self)
        style.configure('CFrame.TFrame', background='Yellow')
        self.config(style='CFrame.TFrame')
        label = ttk.Label(self, text='CFrame')
        label.pack(padx=10, pady=10, anchor=tk.CENTER)
 
 
class DFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style = ttk.Style(self)
        style.configure('DFrame.TFrame', background='Brown')
        self.config(style='DFrame.TFrame')
        label = ttk.Label(self, text='DFrame')
        label.pack(padx=10, pady=10, anchor=tk.CENTER)
 
 
class ReportsFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style = ttk.Style(self)
        style.configure('ReportsFrame.TFrame', background='Orange')
        self.config(style='ReportsFrame.TFrame')
        label = ttk.Label(self, text='ReportsFrame')
        label.pack(padx=10, pady=10, anchor=tk.CENTER)
 
 
class QueriesFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style = ttk.Style(self)
        style.configure('QueriesFrame.TFrame', background='Pink')
        self.config(style='QueriesFrame.TFrame')
        label = ttk.Label(self, text='QueriesFrame')
        label.pack(padx=10, pady=10, anchor=tk.CENTER)
 
 
if __name__ == '__main__':
    app = App()
    app.mainloop()