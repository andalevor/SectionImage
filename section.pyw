#!/bin/env python

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy as np
import pysedaman as sn
import tkinter as tk
from tkinter import filedialog as fd
from PIL import Image, ImageTk
import sys
import os

class SectionImage:
    def __init__(self, in_file = None, out_file = None):
        self.clip = 0.75
        self.cps = 10
        self.tpc = 100
        if not in_file or not out_file:
            self.in_set = False
            self.out_set = False
            self.gui = True

            toz_logo = "TOZ.jpg"
            if getattr(sys, "frozen", False):
                toz_logo = os.path.join(sys._MEIPASS, toz_logo)
            image = Image.open(toz_logo)
            im_w, im_h = image.size
            window = tk.Tk()
            window.minsize(int(im_w * 2.5 + im_h), im_h * 2)
            window.title("Seis image")
            window.columnconfigure(0, weight=1, minsize=im_w/2)
            window.columnconfigure(1, weight=1, minsize=im_w)
            window.columnconfigure(2, weight=1, minsize=im_h)
            for row in range(4):
                window.rowconfigure(row, weight=1, minsize=im_h/2)
            btn_open: Button  = tk.Button(text="Open file", command=self.open_file)
            btn_open.grid(row=0, column=0, padx=5, pady=5, sticky="wens")
            self.lbl_open: Label  = tk.Label()
            self.lbl_open.grid(row=0, column=1, columnspan=3)
            btn_save: Button  = tk.Button(text="Save file", command=self.save_file)
            btn_save.grid(row=1, column=0, padx=5, pady=5, sticky="wens")
            self.lbl_save: Label  = tk.Label()
            self.lbl_save.grid(row=1, column=1, columnspan=3)
            lbl_tpc = tk.Label(text="Traces per cm:")
            lbl_tpc.grid(row=2, column=0, padx=5, pady=5, sticky="wens")
            self.ent_tpc = tk.Entry()
            self.ent_tpc.insert(0, str(self.tpc))
            self.ent_tpc.grid(row=2, column=1, padx=5, pady=5, sticky="wens")
            lbl_cps = tk.Label(text="cm per second:")
            lbl_cps.grid(row=3, column=0, padx=5, pady=5, sticky="wens")
            self.ent_cps = tk.Entry()
            self.ent_cps.insert(0, str(self.cps))
            self.ent_cps.grid(row=3, column=1, padx=5, pady=5, sticky="wens")
            self.btn_go = tk.Button(text="Go", state=tk.DISABLED, command=self.go)
            self.btn_go.grid(row=2, column=2, rowspan=2, padx=5, pady=5, sticky="wens")
            photo = ImageTk.PhotoImage(image)
            canvas = tk.Canvas(window, height=im_h, width=im_w)
            image = canvas.create_image(0, 0, anchor="nw", image=photo)
            canvas.grid(row=2, column=3, rowspan=2)
            lbl_auth = tk.Label(text="Author: Andrei Voronin Email: andrei.a.voronin@gmail.com")
            lbl_auth.grid(row=4, column=2, columnspan=2)

            window.mainloop()
        else:
            self.in_filename = in_file
            self.out_filename = out_file
            self.gui = False
            self.read_data()
            self.create_image()

    def get_tpc(self):
        if self.gui:
            return int(self.ent_tpc.get())
        else:
            return self.tpc

    def get_cps(self):
        if self.gui:
            return int(self.ent_cps.get())
        else:
            return self.cps

    def clip_data(self):
        self.max_val = self.data.max()
        self.min_val = self.data.min()
        max_val = self.max_val if self.max_val > abs(self.min_val) else abs(self.min_val)
        for i in range(self.trace_num):
            for j in range(self.samp_num):
                if abs(self.data[i][j]) > max_val * self.clip:
                    self.data[i][j] *= self.clip

    def read_data(self):
        if os.name == "nt":
            isgy = sn.ISEGY(self.in_filename.encode("cp1251"))
        else:
            isgy = sn.ISEGY(self.in_filename)

        samp_num = isgy.binary_header().samp_per_tr
        ext_samp_per_tr = isgy.binary_header().ext_samp_per_tr
        self.samp_num = ext_samp_per_tr if ext_samp_per_tr != 0 else samp_num
        samp_int = isgy.binary_header().samp_int
        ext_samp_int = isgy.binary_header().ext_samp_int
        self.samp_int = ext_samp_int if ext_samp_int != 0 else samp_int

        first_trace = True
        trace_list = []
        for trc in isgy:
            trace_list.append(trc)
            if first_trace:
                first_trace = False
                self.min_cdp = trc.header().get("ENS_NO")
                self.max_cdp = trc.header().get("ENS_NO")
                continue
            cdp = trc.header().get("ENS_NO")
            if cdp < self.min_cdp:
                self.min_cdp = cdp
            if cdp > self.max_cdp:
                self.max_cdp = cdp

        self.trace_num = len(trace_list)
        self.max_time_ms = (self.samp_num - 1) * self.samp_int / 1000
        self.data = np.zeros((self.trace_num, self.samp_num))
        i = 0
        for trc in trace_list:
            samples = trc.samples()
            for j in range(samp_num):
                self.data[i][j] = samples[j]
            i += 1

    def create_image(self):
        self.clip_data()
        ungf_logo = "ungf.png"
        if getattr(sys, "frozen", False):
            ungf_logo = os.path.join(sys._MEIPASS, ungf_logo)
        logo = plt.imread(ungf_logo)
        logo_width = logo.shape[1]
        fig, ax = plt.subplots()
        bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        axwidth, axheight = bbox.width / 4, bbox.height / 4
        trace_per_cm = self.get_tpc()
        fig_width = self.trace_num / trace_per_cm * 2.54 + logo_width / fig.dpi + axwidth
        cm_per_sec = self.get_cps()
        fig_height = self.max_time_ms / 1000 * cm_per_sec / 2.54 + axheight
        fig.set_size_inches(fig_width, fig_height)
        norm = mcolors.TwoSlopeNorm(vmin=self.min_val * self.clip, vcenter=0, vmax=self.max_val * self.clip)
        im = plt.imshow(self.data.T, cmap="seismic", aspect="auto")
        cpad = 1 - (fig_width - logo_width / 2 / fig.dpi) / fig_width 
        cax = inset_axes(ax, width=0.5, height=10, loc="center right",
                         bbox_to_anchor=(cpad, 0, 1, 1), bbox_transform=ax.transAxes,
                         borderpad=0)
        plt.colorbar(im, cax=cax)
        yticks_step = 500 if self.max_time_ms // 1000 <= 10 else 1000
        yticks_step = yticks_step / self.samp_int * 1000
        yticks = np.arange(0, self.samp_num, int(yticks_step))
        ax.yaxis.set_major_locator(mticker.FixedLocator(yticks))
        ax.set_yticklabels(yticks * self.samp_int / 1000)
        xticks_step = 100
        xticks = np.arange(0, self.max_cdp - self.min_cdp, xticks_step)
        ax.xaxis.set_major_locator(mticker.FixedLocator(xticks))
        ax.set_xticklabels(xticks + self.min_cdp)
        ax.xaxis.tick_top()
        bbox = fig.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        figwidth = bbox.width*fig.dpi
        fig.figimage(logo, figwidth - logo_width)

        rpad = (fig_width - logo_width / fig.dpi) / fig_width
        lpad = 1 - (fig_width - axwidth) / fig_width
        tpad = (fig_height - axheight) / fig_height
        plt.subplots_adjust(left=lpad, bottom=0, right=rpad, top=tpad, wspace=0, hspace=0)
        fig.savefig(self.out_filename)
        plt.close()
        #  plt.show()

    def open_file(self):
        filename = fd.askopenfilename()
        if filename:
            self.in_filename = filename
            self.in_set = True
            self.lbl_open.config(text=self.in_filename)
            if self.out_set:
                self.btn_go["state"] = "normal"

    def save_file(self):
        filename = fd.asksaveasfilename(defaultextension=".png")
        if filename:
            self.out_filename = filename
            self.out_set = True
            self.lbl_save.config(text=self.out_filename)
            if self.in_set:
                self.btn_go["state"] = "normal"

    def go(self):
        if not self.ent_tpc.get().isdigit() or not self.ent_cps.get().isdigit():
            tk.messagebox.showerror(title="Error", message="Entry values must be numbers")
            return
        self.read_data()
        self.create_image()

if __name__ == "__main__":
    SectionImage()
