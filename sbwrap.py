#!/usr/bin/env python3

import tkinter as tk
import tkinter.ttk as ttk

def data():
    for i in range(50):
       ttk.Label(frame,text=i).grid(row=i,column=0)
       ttk.Label(frame,text="my text"+str(i)).grid(row=i,column=1)
       ttk.Label(frame,text="..........").grid(row=i,column=2)

def myfunction(event):
    canvas.configure(scrollregion=canvas.bbox("all"),width=200,height=300)

if __name__ == '__main__':
    root=tk.Tk()
    
    canvas=tk.Canvas(root)
    frame=ttk.Frame(canvas)
    myscrollbar=tk.Scrollbar(root,orient="vertical",command=canvas.yview)
    canvas.configure(yscrollcommand=myscrollbar.set)
    
    myscrollbar.pack(side="right",fill="y")
    canvas.pack(side="left")
    canvas.create_window((0,0),window=frame,anchor='nw')
    frame.bind("<Configure>",myfunction)
    data()
    root.mainloop()
