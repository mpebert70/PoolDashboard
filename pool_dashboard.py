#!/usr/bin/env python3

__author__    = "Michael P. Ebert"
__copyright__ = "Copyright (C) 2017, Michael P. Ebert"
__version__   = "V2.4.0_2017"

try:
    # for python2
    import Tkinter as tk
except ImportError:
    # for python3
    import tkinter as tk
try:
    # for python2
    import ttk
except ImportError:
    # for python3
    import tkinter.ttk as ttk
try:
    # for python2
    import tkFont
except ImportError:
    # for python3
    import tkinter.font as tkFont
try:
    # for python2
    import Queue as queue
except ImportError:
    # for python3
    import queue
import sys
from PIL import Image, ImageTk
import requests
import random
from datetime import datetime, timedelta
from multiprocessing import Process, Queue
import tweepy
import os
import time
import argparse

CAP = 248  # 248 is the standard capacity
MAX_CL = 10.0
MIN_CL = 1.0

def get_api(cfg):
  auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
  auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
  return tweepy.API(auth)


class Dialog(tk.Toplevel):

    def __init__(self, parent, title = None):

        tk.Toplevel.__init__(self, parent)
        self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        self.buttonbox()

        self.wait_visibility()
        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        #self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
        #                          parent.winfo_rooty()+50))

        self.initial_focus.focus_set()

        self.wait_window(self)

    #
    # construction hooks

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden

        pass

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons

        box = tk.Frame(self)

        w = tk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w.bind('<Return>', self.ok)
        w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w.bind('<Return>', self.cancel)

        self.bind("<Escape>", self.cancel)

        box.pack()

    #
    # standard button semantics

    def ok(self, event=None):

        if not self.validate():
            self.initial_focus.focus_set() # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()

    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks

    def validate(self):

        return 1 # override

    def apply(self):

        pass # override


class ExitDialog(Dialog):

    def __init__(self, parent, log_dir, event_log_filename, title = "Quit"):
        if log_dir:
            self.event_log_filename = event_log_filename
            self.log_dir = log_dir
        Dialog.__init__(self, parent, title)

    def buttonbox(self):
        box = tk.Frame(self)

        w = tk.Button(box, text="Yes", width=10, command=self.exit)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w.bind('<Return>',self.exit)
        w = tk.Button(box, text="No", width=10, command=self.cancel, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w.bind('<Return>',self.cancel)
        w.focus_set()

        self.bind("<Escape>", self.cancel)

        box.pack()


    def body(self, master):

        tk.Label(master, text="Are you sure you want to quit?").grid(row=0)
        return

    def exit(self, event=None):
        # add entry to event log indicating that the program is exiting
        time_stamp = datetime.now().strftime("%x %H:%M")
        event_log_file =  open(self.log_dir+self.event_log_filename, "a")
        event_log_file.write("%s, %s, %s, %s\n" % (time_stamp,
                                                   "End",
                                                   None,
                                                   None))
        event_log_file.close()

        self.destroy()
        sys.exit()

class ErrorDialog(Dialog):

    def __init__(self, parent, msg = "Error", title = "Error"):
        if msg:
            self.msg = msg
        Dialog.__init__(self, parent, title)


    def buttonbox(self):
        box = tk.Frame(self)

        w = tk.Button(box, text="OK", width=10, command=self.exit)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w.bind('<Return>',self.exit)
        w.focus_set()

        self.bind("<Escape>", self.cancel)

        box.pack()


    def body(self, master):
        try:
            tk.Label(master, image="::tk::icons::error").grid(row=0, column=0, padx=20)
        except:
            pass
        tk.Label(master, text=self.msg).grid(row=2, column=1, pady=5)
        try:
            tk.Label(master, image="::tk::icons::error").grid(row=0, column=2, padx=20)
        except:
            pass
        return

    def exit(self, event=None):
        self.destroy()


class OperatorDialog(Dialog):

    def body(self, master):

        tk.Label(master, text="Operator Name:").grid(row=0)

        self.e1 = tk.Entry(master)

        self.e1.grid(row=0, column=1)
        return self.e1 # initial focus

    def apply(self):
        name = self.e1.get()
        self.result =  name # or something


class StatusDialog(Dialog):

    def __init__(self, parent, screen_h, log_dir, event_log_filename,
                 twitter_enabled, title = "Update Status"):
        if screen_h:
            self.screen_h = screen_h
            self.event_log_filename = event_log_filename
            self.log_dir = log_dir
            self.twitter_enabled = twitter_enabled
        Dialog.__init__(self, parent, title)

    def body(self, master):

        # add a combobox for selecting the new status
        tk.Label(master, text="Status:", pady=5).grid(row=0, sticky=tk.E)
        self.status_list = ttk.Combobox(master, state="readonly")
        self.status_list['values'] = (' Open',
                                      ' Closed',
                                      ' Wading Pool Closed',
                                      ' Main Pool Closed')
        self.status_list.current(0)  # Open
        self.status_list.bind('<<ComboboxSelected>>', self.status_selected)
        self.status_list.grid(row=0, column=1, sticky=tk.W)

        # add comboxbox for selecting the reason the pool is closed
        self.reason_label = tk.Label(master, text="Reason:", pady=5)
        self.reason_label.grid(row=1, sticky=tk.E)
        self.reason_label.grid_remove()
        self.reason_list = ttk.Combobox(master, width=22, state="readonly")
        self.reason_list['values'] = (' Thunder/Lightning',
                                      ' Water Contamination',
                                      ' Improper Water Chemistry',  
                                      ' Extreme Weather',
                                      ' For The Night')
        self.reason_list.current(0)  # Thunder/Lightning
        self.reason_list.bind('<<ComboboxSelected>>', self.reason_selected)
        self.reason_list.grid(row=1, column=1, sticky=tk.W)
        self.reason_list.grid_remove()

        # add an entry widget for the reopen time
        self.reopen_label = tk.Label(master, text="Reopen Time:", pady=5)
        self.reopen_label.grid(row=2, sticky=tk.E)
        self.reopen_label.grid_remove()
        self.reopen_time_frame = tk.Frame(master)

        self.reopen_hour_sv = tk.StringVar()
        self.reopen_hour_sv.trace("w", lambda name, index, mode, sv=self.reopen_hour_sv: self.sv_callback(sv))

        self.reopen_hour = ttk.Entry(self.reopen_time_frame, width=2, textvariable=self.reopen_hour_sv)
        self.reopen_hour.grid(row=0, column=0, sticky=tk.W)
        tk.Label(self.reopen_time_frame, text=":").grid(row=0,column=1)

        self.reopen_min_sv = tk.StringVar()
        self.reopen_min_sv.trace("w", lambda name, index, mode, sv=self.reopen_min_sv: self.sv_callback(sv))

        self.reopen_min = ttk.Entry(self.reopen_time_frame, width=2, textvariable=self.reopen_min_sv)
        self.reopen_min.grid(row=0, column=2, sticky=tk.W)
        self.reopen_am_pm=ttk.Combobox(self.reopen_time_frame, state="readonly", width=3)
        self.reopen_am_pm['values'] = ('AM','PM')
        self.reopen_am_pm.current(1)  # PM
        self.reopen_am_pm.bind('<<ComboboxSelected>>', self.reopen_am_pm_selected)
        self.reopen_am_pm.grid(row=0, column=3, sticky=tk.W)

        self.reopen_time_frame.grid(row=2, column=1, sticky=tk.W)
        self.reopen_time_frame.grid_remove()

        # add a checkbutton for the tweet feature
        if self.twitter_enabled:
            self.tweet_frame = tk.Frame(master)

            self.send_tweet = tk.IntVar()
            box_size = int(self.screen_h*0.025)
            self.check_image = Image.open("images/check-mark-%s.png" % box_size)
            self.check_tkimage = ImageTk.PhotoImage(self.check_image)

            self.no_check_image = Image.open("images/no-check-mark-%s.png" % box_size)
            self.no_check_tkimage = ImageTk.PhotoImage(self.no_check_image)

            self.tweet_checkbutton = tk.Checkbutton(self.tweet_frame,
                                                    variable=self.send_tweet,
                                                    indicatoron=False,
                                                    background='#ffffff',
                                                    highlightcolor='#ffffff',
                                                    selectcolor='#ffffff',
                                                    offrelief=tk.SUNKEN,
                                                    image=self.no_check_tkimage,
                                                    selectimage=self.check_tkimage)
            self.tweet_label = tk.Label(self.tweet_frame, text="Send Tweet")
            self.tweet_label.bind("<Button-1>", lambda e : self.tweet_checkbutton.toggle())

            self.tweet_checkbutton.grid(row=0, column=0, padx=5, sticky=tk.W)
            self.tweet_label.grid(row=0, column=1, sticky=tk.W)
            self.tweet_frame.grid(row=4, column=0, padx=5, pady=10, sticky=tk.W)

        # return the widget that should get the initial focus
        return self.status_list

    def sv_callback(self, sv):
        if len(sv.get()) > 0:
            if not sv.get()[-1].isdigit():
                c = sv.get()[0:-1]
                sv.set(c)
        c = sv.get()[0:2]
        sv.set(c)

    def status_selected(self, event):
        if self.status_list.current() == 0:  # Open
            self.reason_label.grid_remove()
            self.reason_list.grid_remove()
            self.reopen_label.grid_remove()
            self.reopen_time_frame.grid_remove()
            if self.twitter_enabled:
                self.tweet_checkbutton.deselect()
        else:  # something is closed
            if self.status_list.current() == 1:  # both pools are closed
                self.reason_list.current(0)  # set Thunder/Lightning
                if self.twitter_enabled:
                    self.tweet_checkbutton.select()
            else:  # only one or the other closed
                self.reason_list.current(1)  # set Water Contamination
                if self.twitter_enabled:
                    self.tweet_checkbutton.select()
            self.reason_label.grid()
            self.reason_list.grid()
            self.reopen_label.grid()
            self.reopen_time_frame.grid()
            self.reason_selected(event)
        self.status_list.selection_clear()

    def reason_selected(self, event):
        if self.reason_list.current() == 0:  # Thunder/Lightning
            self.status_list.current(1)  # set closed
            thirty_minutes_from_now = datetime.now() + timedelta(minutes=30)
            self.reopen_hour_sv.set(thirty_minutes_from_now.strftime('%I'))
            self.reopen_min_sv.set(thirty_minutes_from_now.strftime('%M'))
            if 'PM' == thirty_minutes_from_now.strftime('%p'):
                self.reopen_am_pm.current(1)  # set PM
            else:
                self.reopen_am_pm.current(0)  # set AM
        elif self.reason_list.current() == 4:  # closed for the night
            self.status_list.current(1)  # set closed
            if self.twitter_enabled:
                self.tweet_checkbutton.deselect()  # uncheck send tweet
            self.reopen_hour_sv.set('11')
            self.reopen_min_sv.set('00')
            self.reopen_am_pm.current(0)  # set AM
        else:
            self.reopen_am_pm.current(1)  # set PM
            self.reopen_hour_sv.set('')
            self.reopen_min_sv.set('')
            if self.twitter_enabled:
                self.tweet_checkbutton.select()  # check send tweet
        self.reason_list.selection_clear()

    def reopen_am_pm_selected(self, event):
        self.reopen_am_pm.selection_clear()

    def validate(self):
        error_msg = "%s:%s %s\n\nis not a valid time!" % (self.reopen_hour.get(),
                                                          self.reopen_min.get(),
                                                          self.reopen_am_pm.get())
        if self.status_list.current() == 0:  # Open
            return 1

        try:
            self.reopen_hour_int = int(self.reopen_hour.get())
        except ValueError:
            d = ErrorDialog(self, msg=error_msg)
            return 0

        if len(self.reopen_min.get()) != 2:
            d = ErrorDialog(self, msg=error_msg)
            return 0

        try:
            self.reopen_min_int = int(self.reopen_min.get())
        except ValueError:
            d = ErrorDialog(self, msg=error_msg)
            return 0

        if self.reopen_hour_int not in range(1,13):
            d = ErrorDialog(self, msg=error_msg)
            return 0

        if self.reopen_min_int not in range(0,60):
            d = ErrorDialog(self, msg=error_msg)
            return 0
        else:
            return 1 


    def apply(self):
        result = {}
        result["status"] = self.status_list.get().strip()
        if result["status"] == "Open":
            result["reopen_time"] = ""
            result["reason"] = ""
            result["message"] = "The pool is now open."
        else:
            result["reopen_time"] = "%d:%02d %s" % (self.reopen_hour_int,
                                                  self.reopen_min_int,
                                                  self.reopen_am_pm.get())
            result["reason"] = self.reason_list.get().strip()
            base_msg = "The %s is closed due to %s and is scheduled to reopen at %s."
            alt_msg = "The %s is closed %s and is scheduled to reopen at %s."
            if result["status"] == "Closed":
                if result["reason"] == "For The Night":
                    result["message"] = alt_msg % ("pool", result["reason"].lower(), result["reopen_time"])
                else:
                    result["message"] = base_msg % ("pool", result["reason"].lower(), result["reopen_time"])
            elif result["status"] == "Wading Pool Closed":
                result["message"] = base_msg % ("wading pool", result["reason"].lower(), result["reopen_time"])
            elif result["status"] == "Main Pool Closed":
                result["message"] = base_msg % ("main pool", result["reason"].lower(), result["reopen_time"])
            else:
                result["message"] = ""

        # check to see if a tweet should be sent
        if self.twitter_enabled and self.send_tweet.get():
            result["send_tweet"] = True
        else:
            result["send_tweet"] = False

        self.result = result

        # log event to file
        time_stamp = datetime.now().strftime("%x %H:%M")
        event_log_file =  open(self.log_dir+self.event_log_filename, "a")
        event_log_file.write("%s, %s, %s, %s\n" % (time_stamp,
                                                   result["status"],
                                                   result["reason"],
                                                   result["send_tweet"]))
        event_log_file.close()


class ReadingsDialog(Dialog):

    def __init__(self, parent, current, title = "Enter New Readings"):
        self.current = current
        Dialog.__init__(self, parent, title)

    def body(self, master):
        tk.Label(master, text="Time:").grid(row=0, sticky=tk.W)
        tk.Label(master, text="Main").grid(row=1,column=1)
        tk.Label(master, text="Wading").grid(row=1,column=2)
        tk.Label(master, text="Chlorine:").grid(row=2, sticky=tk.W)
        tk.Label(master, text="pH:").grid(row=3, sticky=tk.W)
        tk.Label(master, text="Water Temp:").grid(row=4, sticky=tk.W)

        current_time = datetime.now().strftime("%I:%M %p")
        self.time = tk.Entry(master, width=10)
        self.time.insert(0, current_time)
        self.main_chlorine = tk.Entry(master, width=10)
        self.main_chlorine.insert(0,self.current["main_chlorine"])
        self.wading_chlorine = tk.Entry(master, width=10)
        self.wading_chlorine.insert(0,self.current["wading_chlorine"])
        self.main_ph = tk.Entry(master, width=10)
        self.main_ph.insert(0,self.current["main_ph"])
        self.wading_ph = tk.Entry(master, width=10)
        self.wading_ph.insert(0,self.current["wading_ph"])
        self.main_temp = tk.Entry(master, width=10)
        self.main_temp.insert(0,self.current["main_temp"])
        self.wading_temp = tk.Entry(master, width=10)
        self.wading_temp.insert(0,self.current["wading_temp"])

        self.time.grid(row=0, column=1)
        self.main_chlorine.grid(row=2, column=1)
        self.main_ph.grid(row=3, column=1)
        self.main_temp.grid(row=4, column=1)
        self.wading_chlorine.grid(row=2, column=2)
        self.wading_ph.grid(row=3, column=2)
        self.wading_temp.grid(row=4, column=2)
        tk.Label(master, text="ppm").grid(row=2, column=3, sticky=tk.W)
        tk.Label(master, text=u"\N{DEGREE SIGN}F").grid(row=4, column=3, sticky=tk.W)

        return self.time # initial focus

    def validate(self):
        try:
            datetime.strptime(self.time.get(), '%I:%M %p')
        except ValueError:
            error_msg = "%s\n\nis not a valid time!" % (self.time.get())
            d = ErrorDialog(self, msg=error_msg)
        else:
            return 1 

    def apply(self):
        result = {}
        result["time"] = self.time.get().lstrip("0")
        result["main_chlorine"] = self.main_chlorine.get()
        result["wading_chlorine"] = self.wading_chlorine.get()
        result["main_ph"] = self.main_ph.get()
        result["wading_ph"] = self.wading_ph.get()
        result["main_temp"] = self.main_temp.get()
        result["wading_temp"] = self.wading_temp.get()
        self.result =  result


class MainWindow(object):

    def __init__(self, master, screen_dimensions):
        self.master = master
        self.screen_dimensions = screen_dimensions
        self.screen_w = int(screen_dimensions.split("x")[0])
        self.screen_h = int(screen_dimensions.split("x")[1])

        # check to see if log directory exists, if not create it
        self.log_dir = os.path.expanduser("~/logs/")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # check to see if log file exists, if not create it and write header
        self.log_filename = "facility_time_hist_%s.csv" % datetime.today().year
        if not os.path.isfile(self.log_dir+self.log_filename):
            log_file =  open(self.log_dir+self.log_filename, "a")
            log_file.write("%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s\n" % 
                                         ("time_stamp",
                                          "count",
                                          "status",
                                          "reason",
                                          "reading time",
                                          "main chlorine",
                                          "wading chlorine",
                                          "main ph",
                                          "wading ph",
                                          "main temp",
                                          "wading temp",
                                          "air temp",
                                          "conditions",
                                          "manager"))
            log_file.close()

        # check to see if event log file exists, if not create it and write header
        self.event_log_filename = "facility_event_log_%s.csv" % datetime.today().year
        if not os.path.isfile(self.log_dir+self.event_log_filename):
            event_log_file = open(self.log_dir+self.event_log_filename, "a")
            event_log_file.write("%s, %s, %s, %s\n" % ("time_stamp",
                                                       "status",
                                                       "reason",
                                                       "tweet"))
            event_log_file.close()

        # add entry to event log indicating that the program has started
        time_stamp = datetime.now().strftime("%x %H:%M")
        event_log_file =  open(self.log_dir+self.event_log_filename, "a")
        event_log_file.write("%s, %s, %s, %s\n" % (time_stamp,
                                                   "Start",
                                                   None,
                                                   None))
        event_log_file.close()

        self.just_logged = False
        self.count = 0
        self.status_text = "Open"
        self.reason_text = ""
        self.reopen_time_text = ""
        self.water_quality_time_text = ""
        self.main_chlorine_text = ""
        self.wading_chlorine_text = ""
        self.main_ph_text = ""
        self.wading_ph_text = ""
        self.main_temp_text = ""
        self.wading_temp_text = ""
        self.q = Queue()
        self.temp_f = None
        self.feelslike = None
        self.conditions = None
        self.sunrise = None
        self.sunset = None
        self.operator_name_text = None

        # twitter setup
        try:
            twitter_cfg = {"consumer_key"        : os.environ["TWITTER_CONSUMER_KEY"],
                           "consumer_secret"     : os.environ["TWITTER_CONSUMER_SECRET"],
                           "access_token"        : os.environ["TWITTER_ACCESS_TOKEN"],
                           "access_token_secret" : os.environ["TWITTER_ACCESS_TOKEN_SECRET"]}
        except KeyError as e:
            self.twitter_enabled = False
        else:
            self.twitter_enabled = True
            self.twitter_api = get_api(twitter_cfg)

        self.master.bind("<Escape>", self.exit)
        self.master.bind("<Key>", self.key_callback)
        self.master.focus_force()

        self.canvas = tk.Canvas(master, 
                                width=self.screen_w,
                                height=self.screen_h,
                                bd=0,
                                highlightthickness=0)
        self.canvas.pack()

        # background image
        bg_image = Image.open("images/poolBackgroundNewLogo%s.png" % self.screen_dimensions)
        self.tkimage = ImageTk.PhotoImage(bg_image)
        self.canvas.create_image(0, 0, image=self.tkimage, anchor=tk.NW)

        # progress bar
        p_x0 = int(round(0.19*self.screen_w))-5
        p_y0 = int(round(0.23*self.screen_h))
        p_x1 = int(round(0.81*self.screen_w))-5
        p_y1 = int(round(0.2925*self.screen_h))
        self.p_width = p_x1 - p_x0
        self.p_height = p_y1 - p_y0
        self.progress = tk.Canvas(master,
                                  width=self.p_width,
                                  height=self.p_height,
                                  relief=tk.RIDGE,
                                  bg="light gray",
                                  bd=int(round(0.0025*self.screen_w)),
                                  highlightthickness=0)
        self.progress_window = self.canvas.create_window(p_x0,
                                                         p_y0,
                                                         anchor=tk.NW,
                                                         window=self.progress)


        # counter
        self.counter = self.canvas.create_text(int(round(0.50*self.screen_w)),
                                               int(round(0.34*self.screen_h)),
                                               text="0/{0}".format(CAP),
                                               font="Verdana %s bold" % int(round(0.05*self.screen_h)),
                                               fill="#0069a5")

        # operator on duty
        self.canvas.create_rectangle(int(round(0.04*self.screen_w)),
                                     int(round(0.38*self.screen_h)),
                                     int(round(0.96*self.screen_w)),
                                     int(round(0.435*self.screen_h)),
                                     fill="white",
                                     outline="white",
                                     tags="operator_area")
        self.operator_label = self.canvas.create_text(int(round(0.05*self.screen_w)), 
                                                      int(round(0.4079*self.screen_h)),
                                                      text="OPERATOR ON DUTY:",
                                                      font="Verdana %s" % int(round(0.033*self.screen_h)),
                                                      anchor=tk.W,
                                                      fill="#0069a5",
                                                      tags="operator_area")
        self.operator_name = self.canvas.create_text(self.canvas.bbox(self.operator_label)[2]+int(round(0.017*self.screen_w)),
                                                     int(round(0.4079*self.screen_h)),
                                                     text="",
                                                     font="Verdana %s bold" % int(round(0.033*self.screen_h)),
                                                     anchor=tk.W,
                                                     fill="sea green",
                                                     tags="operator_area")
        self.canvas.tag_bind("operator_area","<Button-1>",
                             self.enter_operator_name)

        # Status
        self.canvas.create_rectangle(int(round(0.04*self.screen_w)),
                                     int(round(0.455*self.screen_h)),
                                     int(round(0.96*self.screen_w)),
                                     int(round(0.505*self.screen_h)),
                                     fill="white",
                                     outline="white",
                                     tags="status_area")
        self.status_label = self.canvas.create_text(int(round(0.05*self.screen_w)),
                                int(round(0.4808*self.screen_h)),
                                text="STATUS:",
                                font="Verdana %s" % int(round(0.033*self.screen_h)),
                                anchor=tk.W,
                                fill="#0069a5",
                                tags="status_area")
        self.status = self.canvas.create_text(self.canvas.bbox(self.status_label)[2]+int(round(0.017*self.screen_w)),
                                              int(round(0.4808*self.screen_h)),
                                              text=self.status_text,
                                              font="Verdana %s bold" % int(round(0.033*self.screen_h)),
                                              anchor=tk.W,
                                              fill="sea green",
                                              tags="status_area")
        self.canvas.tag_bind("status_area","<Button-1>",
                             self.enter_status)

        self.reopen_label = self.canvas.create_text(int(round(0.5*self.screen_w)),
                                                    int(round(0.4808*self.screen_h)),
                                                    text="REOPEN TIME:",
                                                    font="Verdana %s" % int(round(0.033*self.screen_h)),
                                                    anchor=tk.W,
                                                    fill="#0069a5",
                                                    tags="status_area")
        self.reopen_time = self.canvas.create_text(self.canvas.bbox(self.reopen_label)[2]+int(round(0.017*self.screen_w)),
                                                   int(round(0.4808*self.screen_h)),
                                                   text="",
                                                   font="Verdana %s bold" % int(round(0.033*self.screen_h)),
                                                   anchor=tk.W,
                                                   fill="red",
                                                   tags="status_area")
        # hide the reopen_label by defualt
        self.canvas.itemconfig(self.reopen_label, state=tk.HIDDEN)
        self.canvas.tag_bind("status_area","<Button-1>",
                             self.enter_status)

        # horizontal line
        self.canvas.create_line(int(round(0.03125*self.screen_w)),
                                int(round(0.5329*self.screen_h)),
                                int(round(0.96875*self.screen_w)),
                                int(round(0.5329*self.screen_h)),
                                fill="dim grey",
                                width=int(round(self.screen_h/480.0)))

        # water quality test results
        self.canvas.create_text(int(round(0.5*self.screen_w)),
                                int(round(0.5746*self.screen_h)),
                                text="TODAY'S POOL WATER QUALITY TEST RESULTS",
                                font="Verdana %s" % (int(round(0.04167*self.screen_h))),
                                fill="dim grey")

        # readings table
        self.readings_table(x_pos=0.12, y_pos=0.625)

        # acceptable levels table
        self.acceptable_levels_table(x_pos=0.53, y_pos=0.625)

        # weather
        self.conditions_text = self.canvas.create_text(int(round(0.5*self.screen_w)),
                                int(round(0.885*self.screen_h)),
                                text="weather conditions",
                                font="Verdana %s bold" % (int(round(0.025*self.screen_h))),
                                fill="sea green")

        # clock
        self.clock = self.canvas.create_text(int(round(0.5*self.screen_w)),
                                int(round(0.93*self.screen_h)),
                                text="??:?? ?M",
                                font="Verdana %s bold" % (int(round(0.038*self.screen_h))),
                                fill="sea green")

        # horizontal line
        self.canvas.create_rectangle(int(round(0.0*self.screen_w)),
                                int(round(0.9560*self.screen_h)),
                                int(round(1.0*self.screen_w)),
                                int(round(1.0*self.screen_h)),
                                fill="#1DA1F2",
                                outline="dim grey",
                                width=int(round(self.screen_h/480.0)))

        # twitter banner
        self.canvas.create_text(0.032*self.screen_w,
                                0.992*self.screen_h,
                                text=u"Follow @GBPoolClub",
                                font="Helvetica %s bold" % (int(round(0.019*self.screen_h))),
                                fill="white",
                                anchor=tk.SW)

        twitter_logo = Image.open("images/Twitter_Logo_White_On_Blue-%s.png" % (int(round(0.037*self.screen_h))))
        self.twitter_logo_image = ImageTk.PhotoImage(twitter_logo)
        self.canvas.create_image(0.01*self.screen_w,
                                 0.9960*self.screen_h,
                                 image=self.twitter_logo_image,
                                 anchor=tk.SW)

        # website banner
        self.canvas.create_text(0.99*self.screen_w,
                                0.992*self.screen_h,
                                text=u"http://greenbriar.org/today-the-pool/",
                                font="Helvetica %s bold" % (int(round(0.019*self.screen_h))),
                                fill="white",
                                anchor=tk.SE)

        self.push_count()

        self.update_clock()

        try:
            self.open_weather_api_key = os.environ["OPEN_WEATHER_API_KEY"]
            self.location = os.environ["LAT_LON_POOL"]
            self.lat = self.location.split(',')[0]
            self.lon = self.location.split(',')[1]
        except KeyError:
            self.open_weather_api_key = None
            self.location = None

        if self.open_weather_api_key and self.location:
            self.update_weather()
            self.consume_weather()

    def consume_weather(self):
        try:
            result = self.q.get_nowait()
        except queue.Empty as e:
            pass

        try:
            # Current Temperature in Fahrenheit
            self.temp_f = result["temp_f"]

            # Current Feels Like Temperature in Fahrenheit
            self.feelslike = result["feelslike"]

            # Current Conditions
            self.conditions = result["conditions"]

            # Sunrise Time
            self.sunrise = result["sunrise"]

            # Sunset Time
            self.sunset = result["sunset"]

        except:
            pass

        self.canvas.itemconfig(self.conditions_text,
                               text=u"feels like {}\N{DEGREE SIGN}F - {}".format(self.feelslike, self.conditions))

        # call this method again in 10 seconds
        refresh_period_sec = 10  # seconds
        refresh_period_ms = int(refresh_period_sec * 1000)   # milliseconds
        self.master.after(refresh_period_ms, self.consume_weather)


    def call_open_weather(self, q):
        url = "https://api.openweathermap.org/data/3.0/onecall?units=imperial&lat={0}&lon={1}&appid={2}".format(self.lat, self.lon, self.open_weather_api_key)
        headers = {"Accept-Encoding" : "gzip"}

        try:
            open_weather_dict = requests.get(url, headers=headers).json()
        except (requests.RequestException, ValueError, requests.HTTPError) as e:
            pass
        else:
            result = {}
            result["temp_f"] = round(open_weather_dict['current']['temp'])
            result["feelslike"] = round(open_weather_dict['current']['feels_like'])
            result["conditions"] = open_weather_dict['current']['weather'][0]['description']
            result["sunrise"] = time.localtime(open_weather_dict['daily'][0]['sunrise'])
            result["sunset"] = time.localtime(open_weather_dict['daily'][0]['sunset'])
            q.put(result)
        sys.exit()


    def update_weather(self):

        p = Process(name="weather", target=self.call_open_weather, args=(self.q,))
        p.daemon = True
        p.start()
        # call this method again in 5 minutes
        # updates limited to 1000 per day, and 10 per minute
        refresh_period_min = 5  # minutes
        refresh_period_ms = int(refresh_period_min * 60 * 1000)   # milliseconds
        self.master.after(refresh_period_ms, self.update_weather)


    def update_clock(self):
        self.canvas.itemconfig(self.clock,
                               text=time.strftime("%I:%M %p", time.localtime()).lstrip("0"))

        # log the facility data every 15 minutes
        mod_minutes = int(time.strftime("%M", time.localtime())) % 15
        if (mod_minutes == 0 and self.just_logged == False):
            time_stamp = datetime.now().strftime("%x %H:%M")
            log_file =  open(self.log_dir+self.log_filename, "a")
            log_file.write("%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s\n" % 
                                         (time_stamp,
                                          self.count,
                                          self.status_text,
                                          self.reason_text,
                                          self.water_quality_time_text,
                                          self.main_chlorine_text,
                                          self.wading_chlorine_text,
                                          self.main_ph_text,
                                          self.wading_ph_text,
                                          self.main_temp_text,
                                          self.wading_temp_text,
                                          self.feelslike,
                                          self.conditions,
                                          self.operator_name_text))
            log_file.close()
            self.just_logged = True
            # reset the flag in 90 seconds
            self.master.after(90000, self.reset_just_logged_flag)

        # call this method again in 200 milliseconds (0.2 seconds)
        refresh_period = 200  # 0.2 seconds
        self.master.after(refresh_period, self.update_clock)


    def reset_just_logged_flag(self):
        self.just_logged = False


    def readings_table(self, x_pos, y_pos):
        self.canvas.create_rectangle(int(round((x_pos+0.00)*self.screen_w)),
                                     int(round((y_pos+0.00)*self.screen_h)),
                                     int(round((x_pos+0.35)*self.screen_w)),
                                     int(round(0.9208*self.screen_h)),
                                     fill="white",
                                     outline="white",
                                     tags="readings_area")

        self.canvas.create_text(int(round((x_pos+0.0240)*self.screen_w)),
                                int(round((y_pos+0.0233)*self.screen_h)),
                                text="READINGS",
                                font="Verdana %s" % (int(round(0.02917*self.screen_h))),
                                anchor=tk.W,
                                fill="dim grey",
                                tags="readings_area")
        self.time_label = self.canvas.create_text(
                                int(round((x_pos+0.154)*self.screen_w)),
                                int(round((y_pos+0.0233)*self.screen_h)),
                                text="Recorded: ___________",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W,
                                tags="readings_area")
        self.time = self.canvas.create_text(
                                int(round((x_pos+0.239)*self.screen_w)),
                                int(round((y_pos+0.0233)*self.screen_h)),
                                text="",
                                font="Verdana %s bold" % (int(round(0.02083*self.screen_h))),
                                fill="sea green",
                                anchor=tk.W,
                                tags="readings_area")
        self.canvas.create_line(int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                fill="dim grey",
                                tags="readings_area",
                                width=int(round(self.screen_h/480.0)))  # horizontal
        self.canvas.create_line(int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.1067)*self.screen_h)),
                                int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.1067)*self.screen_h)),
                                fill="dim grey",
                                tags="readings_area",
                                width=int(round(self.screen_h/480.0)))  # horizontal
        self.canvas.create_line(int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                tags="readings_area",
                                width=int(round(self.screen_h/480.0)))  # horizontal
        self.canvas.create_line(int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                tags="readings_area",
                                width=int(round(self.screen_h/480.0)))  # vertical
        self.canvas.create_line(int(round((x_pos+0.11875)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.11875)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                tags="readings_area",
                                width=int(round(self.screen_h/480.0)))  # vertical
        self.canvas.create_line(int(round((x_pos+0.234)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.234)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                tags="readings_area",
                                width=int(round(self.screen_h/480.0)))  # vertical
        self.canvas.create_line(int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                tags="readings_area",
                                width=int(round(self.screen_h/480.0)))  # vertical

        # table headings
        self.canvas.create_text(int(round((x_pos+0.06)*self.screen_w)),
                                int(round((y_pos+0.0817)*self.screen_h)),
                                text="PARAMETER",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                tags="readings_area")
        self.canvas.create_text(int(round((x_pos+0.176)*self.screen_w)),
                                int(round((y_pos+0.0817)*self.screen_h)),
                                text="MAIN",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                tags="readings_area")
        self.canvas.create_text(int(round((x_pos+0.292)*self.screen_w)),
                                int(round((y_pos+0.0817)*self.screen_h)),
                                text="WADING",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                tags="readings_area")
        # first row
        self.canvas.create_text(int(round((x_pos+0.0088)*self.screen_w)),
                                int(round((y_pos+0.1358)*self.screen_h)),
                                text="Chlorine",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W,
                                tags="readings_area")

        self.main_chlorine_center_x = int(round((x_pos+0.176)*self.screen_w))
        self.main_chlorine_center_y = int(round((y_pos+0.1358)*self.screen_h))
        self.main_chlorine = self.canvas.create_text(
                                self.main_chlorine_center_x, 
                                self.main_chlorine_center_y,
                                text="",
                                font="Verdana %s bold" % (int(round(0.02083*self.screen_h))),
                                fill="sea green",
                                tags="readings_area",
                                anchor=tk.W)
        self.main_chlorine_units = self.canvas.create_text(
                                self.main_chlorine_center_x, 
                                self.main_chlorine_center_y,
                                text="ppm",
                                font="Verdana %s bold" % (int(round(0.015*self.screen_h))),
                                fill="sea green",
                                tags="readings_area",
                                anchor=tk.SW)
        self.center_combo(self.main_chlorine,
                          self.main_chlorine_units,
                          self.main_chlorine_center_x, 
                          self.main_chlorine_center_y)

        self.wading_chlorine_center_x = int(round((x_pos+0.292)*self.screen_w))
        self.wading_chlorine_center_y = int(round((y_pos+0.1358)*self.screen_h))
        self.wading_chlorine = self.canvas.create_text(
                                self.wading_chlorine_center_x,
                                self.wading_chlorine_center_y,
                                text="",
                                font="Verdana %s bold" % (int(round(0.02083*self.screen_h))),
                                fill="sea green",
                                tags="readings_area",
                                anchor=tk.W)
        self.wading_chlorine_units = self.canvas.create_text(
                                self.wading_chlorine_center_x,
                                self.wading_chlorine_center_y,
                                text="ppm",
                                font="Verdana %s bold" % (int(round(0.015*self.screen_h))),
                                fill="sea green",
                                tags="readings_area",
                                anchor=tk.SW)
        self.center_combo(self.wading_chlorine,
                          self.wading_chlorine_units,
                          self.wading_chlorine_center_x, 
                          self.wading_chlorine_center_y)
        # second row
        self.canvas.create_text(int(round((x_pos+0.0088)*self.screen_w)),
                                int(round((y_pos+0.1733)*self.screen_h)),
                                text="pH",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W,
                                tags="readings_area")
        self.main_ph = self.canvas.create_text(
                                int(round((x_pos+0.176)*self.screen_w)),
                                int(round((y_pos+0.1733)*self.screen_h)),
                                text="",
                                font="Verdana %s bold" % (int(round(0.02083*self.screen_h))),
                                fill="sea green",
                                tags="readings_area")
        self.wading_ph = self.canvas.create_text(
                                int(round((x_pos+0.292)*self.screen_w)),
                                int(round((y_pos+0.1733)*self.screen_h)),
                                text="",
                                font="Verdana %s bold" % (int(round(0.02083*self.screen_h))),
                                fill="sea green",
                                tags="readings_area")
        # third row
        self.canvas.create_text(int(round((x_pos+0.0088)*self.screen_w)),
                                int(round((y_pos+0.2108)*self.screen_h)),
                                text="Water Temp",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W,
                                tags="readings_area")

        self.main_temp_center_x = int(round((x_pos+0.176)*self.screen_w))
        self.main_temp_center_y = int(round((y_pos+0.2108)*self.screen_h))
        self.main_temp = self.canvas.create_text(
                                self.main_temp_center_x,
                                self.main_temp_center_y,
                                text="",
                                font="Verdana %s bold" % (int(round(0.02083*self.screen_h))),
                                fill="sea green",
                                tags="readings_area",
                                anchor=tk.W)
        self.main_temp_units = self.canvas.create_text(
                                self.main_temp_center_x,
                                self.main_temp_center_y,
                                text=u"\N{DEGREE SIGN}F",
                                font="Verdana %s bold" % (int(round(0.015*self.screen_h))),
                                fill="sea green",
                                tags="readings_area",
                                anchor=tk.SW)
        self.center_combo(self.main_temp,
                          self.main_temp_units,
                          self.main_temp_center_x,
                          self.main_temp_center_y)

        self.wading_temp_center_x = int(round((x_pos+0.292)*self.screen_w))
        self.wading_temp_center_y = int(round((y_pos+0.2108)*self.screen_h))
        self.wading_temp = self.canvas.create_text(
                                self.wading_temp_center_x,
                                self.wading_temp_center_y,
                                text="",
                                font="Verdana %s bold" % (int(round(0.02083*self.screen_h))),
                                fill="sea green",
                                tags="readings_area",
                                anchor=tk.W)
        self.wading_temp_units = self.canvas.create_text(
                                self.wading_temp_center_x,
                                self.wading_temp_center_y,
                                text=u"\N{DEGREE SIGN}F",
                                font="Verdana %s bold" % (int(round(0.015*self.screen_h))),
                                fill="sea green",
                                tags="readings_area",
                                anchor=tk.SW)
        self.center_combo(self.wading_temp,
                          self.wading_temp_units,
                          self.wading_temp_center_x,
                          self.wading_temp_center_y)

        self.canvas.tag_bind("readings_area","<Button-1>",
                             self.enter_readings)


    def acceptable_levels_table(self, x_pos, y_pos):
        self.canvas.create_text(int(round((x_pos+0.175)*self.screen_w)),
                                int(round((y_pos+0.0233)*self.screen_h)),
                                text="ACCEPTABLE LEVELS",
                                font="Verdana %s" % (int(round(0.02917*self.screen_h))),
                                fill="dim grey")
        self.canvas.create_line(int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                fill="dim grey",
                                width=int(round(self.screen_h/480.0)))  # horizontal
        self.canvas.create_line(int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.1067)*self.screen_h)),
                                int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.1067)*self.screen_h)),
                                fill="dim grey",
                                width=int(round(self.screen_h/480.0)))  # horizontal
        self.canvas.create_line(int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                width=int(round(self.screen_h/480.0)))  # horizontal
        self.canvas.create_line(int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.00)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                width=int(round(self.screen_h/480.0)))  # vertical
        self.canvas.create_line(int(round((x_pos+0.11875)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.11875)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                width=int(round(self.screen_h/480.0)))  # vertical
        self.canvas.create_line(int(round((x_pos+0.234)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.234)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                width=int(round(self.screen_h/480.0)))  # vertical
        self.canvas.create_line(int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.0546)*self.screen_h)),
                                int(round((x_pos+0.35)*self.screen_w)),
                                int(round((y_pos+0.2358)*self.screen_h)),
                                fill="dim grey",
                                width=int(round(self.screen_h/480.0)))  # vertical

        # table headings
        self.canvas.create_text(int(round((x_pos+0.06)*self.screen_w)),
                                int(round((y_pos+0.0817)*self.screen_h)),
                                text="PARAMETER",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey")
        self.canvas.create_text(int(round((x_pos+0.176)*self.screen_w)),
                                int(round((y_pos+0.0817)*self.screen_h)),
                                text="MIN",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey")
        self.canvas.create_text(int(round((x_pos+0.292)*self.screen_w)),
                                int(round((y_pos+0.0817)*self.screen_h)),
                                text="MAX",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey")
        # first row
        self.canvas.create_text(int(round((x_pos+0.0088)*self.screen_w)),
                                int(round((y_pos+0.1358)*self.screen_h)),
                                text="Chlorine",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W)

        center_x = int(round((x_pos+0.176)*self.screen_w))
        center_y = int(round((y_pos+0.1358)*self.screen_h))
        a = self.canvas.create_text(center_x,
                                center_y,
                                text="{0:.1f}".format(MIN_CL),
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W)
        b = self.canvas.create_text(center_x,
                                center_y,
                                text="ppm",
                                font="Verdana %s" % (int(round(0.015*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.SW)
        self.center_combo(a, b, center_x, center_y)


        center_x = int(round((x_pos+0.292)*self.screen_w))
        center_y = int(round((y_pos+0.1358)*self.screen_h))
        a = self.canvas.create_text(center_x,
                                center_y,
                                text="{0:.1f}".format(MAX_CL),
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W)
        b = self.canvas.create_text(center_x,
                                center_y,
                                text="ppm",
                                font="Verdana %s" % (int(round(0.015*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.SW)
        self.center_combo(a, b, center_x, center_y)

        # second row
        self.canvas.create_text(int(round((x_pos+0.0088)*self.screen_w)),
                                int(round((y_pos+0.1733)*self.screen_h)),
                                text="pH",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W)
        self.canvas.create_text(int(round((x_pos+0.176)*self.screen_w)),
                                int(round((y_pos+0.1733)*self.screen_h)),
                                text="7.2",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey")
        self.canvas.create_text(int(round((x_pos+0.292)*self.screen_w)),
                                int(round((y_pos+0.1733)*self.screen_h)),
                                text="7.8",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey")

        # third row
        self.canvas.create_text(int(round((x_pos+0.0088)*self.screen_w)),
                                int(round((y_pos+0.2108)*self.screen_h)),
                                text="Water Temp",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W)
        self.canvas.create_text(int(round((x_pos+0.176)*self.screen_w)),
                                int(round((y_pos+0.2108)*self.screen_h)),
                                text="N/A",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey")

        center_x = int(round((x_pos+0.292)*self.screen_w))
        center_y = int(round((y_pos+0.2108)*self.screen_h))
        a = self.canvas.create_text(center_x,
                                center_y,
                                text=u"104",
                                font="Verdana %s" % (int(round(0.02083*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.W)
        b = self.canvas.create_text(center_x,
                                center_y,
                                text=u"\N{DEGREE SIGN}F",
                                font="Verdana %s" % (int(round(0.015*self.screen_h))),
                                fill="dim grey",
                                anchor=tk.SW)
        self.center_combo(a, b, center_x, center_y)


    def center_combo(self, a, b, x_center, y_center):
        # assumes that a is anchor=tk.W and b is anchor=tk.SW
        # compute the width of object a
        bounds_a = self.canvas.bbox(a)
        width_a = bounds_a[2] - bounds_a[0]

        # compute the width of object b      
        bounds_b = self.canvas.bbox(b)
        width_b = bounds_b[2] - bounds_b[0]

        # compute the total width
        width_ab = width_a + width_b

        # compute the west position
        west_ab = x_center - int(round(width_ab/2.0))

        # move object a
        self.canvas.coords(a, west_ab, y_center)

        # move object b
        bounds_a = self.canvas.bbox(a)
        self.canvas.coords(b, bounds_a[2], bounds_a[3])


    def exit(self, event):
        d = ExitDialog(self.master, self.log_dir,
                       self.event_log_filename, title="Quit")

    def enter_operator_name(self, event):
        d = OperatorDialog(self.master, title="Enter New Operator Name")
        self.operator_name_text = d.result
        self.canvas.itemconfig(self.operator_name,
                               text=self.operator_name_text)

    def enter_status(self, event):
        d = StatusDialog(self.master, self.screen_h, self.log_dir,
                         self.event_log_filename, self.twitter_enabled,
                         title="Update Status")
        new_status = d.result
        if new_status:
            self.status_text = new_status["status"]
            self.reason_text = new_status["reason"]
            self.reopen_time_text = new_status["reopen_time"]
            if self.status_text == "Open":
                self.canvas.itemconfig(self.status,
                                       text=self.status_text,
                                       fill="sea green")
                self.canvas.itemconfig(self.reopen_label,
                                       state=tk.HIDDEN)
                self.canvas.itemconfig(self.reopen_time,
                                       state=tk.HIDDEN)
            else:
                self.canvas.itemconfig(self.status,
                                       text=self.status_text,
                                       fill="red")
                self.canvas.itemconfig(self.reopen_label,
                                       state=tk.NORMAL)
                self.canvas.itemconfig(self.reopen_time,
                                       text=self.reopen_time_text)
                self.canvas.itemconfig(self.reopen_time,
                                       state=tk.NORMAL)
            if new_status["send_tweet"] and self.twitter_enabled:
                tweet_status = self.twitter_api.update_status(status=new_status["message"]
                                + " [posted: %s]" % datetime.now().strftime("%I:%M:%S %p, %x").lstrip("0"))

    def enter_readings(self, event):
        current = {"main_chlorine" : self.main_chlorine_text,
                   "wading_chlorine" : self.wading_chlorine_text,
                   "main_ph" : self.main_ph_text,
                   "wading_ph" : self.wading_ph_text,
                   "main_temp" : self.main_temp_text,
                   "wading_temp" : self.wading_temp_text}
        d = ReadingsDialog(self.master, current, title="Enter New Readings")
        readings = d.result
        if readings:
            self.water_quality_time_text = readings["time"]
            self.main_chlorine_text = readings["main_chlorine"]
            self.wading_chlorine_text = readings["wading_chlorine"]
            self.main_ph_text = readings["main_ph"]
            self.wading_ph_text = readings["wading_ph"]
            self.main_temp_text = readings["main_temp"]
            self.wading_temp_text = readings["wading_temp"]
            self.canvas.itemconfig(self.time,
                                   text=self.water_quality_time_text)
            self.canvas.itemconfig(self.main_chlorine,
                                   text=self.main_chlorine_text)
            self.center_combo(self.main_chlorine,
                              self.main_chlorine_units,
                              self.main_chlorine_center_x,
                              self.main_chlorine_center_y)

            self.canvas.itemconfig(self.wading_chlorine,
                                   text=self.wading_chlorine_text)
            self.center_combo(self.wading_chlorine,
                              self.wading_chlorine_units,
                              self.wading_chlorine_center_x,
                              self.wading_chlorine_center_y)

            self.canvas.itemconfig(self.main_ph,
                                   text=self.main_ph_text)
            self.canvas.itemconfig(self.wading_ph,
                                   text=self.wading_ph_text)
            self.canvas.itemconfig(self.main_temp,
                                   text=self.main_temp_text)
            self.center_combo(self.main_temp,
                              self.main_temp_units,
                              self.main_temp_center_x,
                              self.main_temp_center_y)

            self.canvas.itemconfig(self.wading_temp,
                                   text=self.wading_temp_text)
            self.center_combo(self.wading_temp,
                              self.wading_temp_units,
                              self.wading_temp_center_x,
                              self.wading_temp_center_y)

            # adjust color if out of range
            try:
                if float(self.main_chlorine_text) >= MIN_CL and float(self.main_chlorine_text) <= MAX_CL:
                    self.canvas.itemconfig(self.main_chlorine, fill="sea green")
                    self.canvas.itemconfig(self.main_chlorine_units, fill="sea green")
                else:
                    self.canvas.itemconfig(self.main_chlorine, fill="red")
                    self.canvas.itemconfig(self.main_chlorine_units, fill="red")
            except:
                self.canvas.itemconfig(self.main_chlorine, fill="red")
                self.canvas.itemconfig(self.main_chlorine_units, fill="red")
            try:
                if float(self.wading_chlorine_text) >= MIN_CL and float(self.wading_chlorine_text) <= MAX_CL:
                    self.canvas.itemconfig(self.wading_chlorine, fill="sea green")
                    self.canvas.itemconfig(self.wading_chlorine_units, fill="sea green")
                else:
                    self.canvas.itemconfig(self.wading_chlorine, fill="red")
                    self.canvas.itemconfig(self.wading_chlorine_units, fill="red")
            except:
                self.canvas.itemconfig(self.wading_chlorine, fill="red")
                self.canvas.itemconfig(self.wading_chlorine_units, fill="red")

            try:
                if float(self.main_ph_text) >= 7.2 and float(self.main_ph_text) <= 7.8:
                    self.canvas.itemconfig(self.main_ph, fill="sea green")
                else:
                    self.canvas.itemconfig(self.main_ph, fill="red")
            except:
                self.canvas.itemconfig(self.main_ph, fill="red")
            try:
                if float(self.wading_ph_text) >= 7.2 and float(self.wading_ph_text) <= 7.8:
                    self.canvas.itemconfig(self.wading_ph, fill="sea green")
                else:
                    self.canvas.itemconfig(self.wading_ph, fill="red")
            except:
                self.canvas.itemconfig(self.wading_ph, fill="red")

            try:
                if float(self.main_temp_text) <= 104.0:
                    self.canvas.itemconfig(self.main_temp, fill="sea green")
                    self.canvas.itemconfig(self.main_temp_units, fill="sea green")
                else:
                    self.canvas.itemconfig(self.main_temp, fill="red")
                    self.canvas.itemconfig(self.main_temp_units, fill="red")
            except:
                self.canvas.itemconfig(self.main_temp, fill="red")
                self.canvas.itemconfig(self.main_temp_units, fill="red")
            try:
                if float(self.wading_temp_text) <= 104.0:
                    self.canvas.itemconfig(self.wading_temp, fill="sea green")
                    self.canvas.itemconfig(self.wading_temp_units, fill="sea green")
                else:
                    self.canvas.itemconfig(self.wading_temp, fill="red")
                    self.canvas.itemconfig(self.wading_temp_units, fill="red")
            except:
                self.canvas.itemconfig(self.wading_temp, fill="red")
                self.canvas.itemconfig(self.wading_temp_units, fill="red")


    def key_callback(self, event):
        try:
            if event.char == '+' or event.char == "=" or event.keysym == "Right":
                self.count += 1
                if self.count > 249:
                    self.count = 249
            elif event.char == '-' or event.char == "_" or event.keysym == "Left":
                self.count -= 1
                if self.count < 0:
                    self.count = 0
            else:
                return
        except:
            pass

        # progress bar
        offset = int(round(self.screen_w*0.00375))
        total_length = self.p_width - int(round(offset/2.0))+1
        self.progress.delete("all")
        if self.count > CAP:
            self.draw_gradient(offset+int(round(total_length*CAP/float(CAP))),
                               self.p_height,
                               "gray50",
                               "black",offset)
            self.canvas.itemconfig(self.counter,
                                   text=u"\N{SKULL AND CROSSBONES} {0}/{1} \N{SKULL AND CROSSBONES}".format(self.count,CAP),
                                   fill="black")
        elif self.count > int(0.90*CAP):
            self.draw_gradient(offset+int(round(total_length*self.count/float(CAP))),
                               self.p_height,
                               "tomato",
                               "coral4",offset)
            self.canvas.itemconfig(self.counter,
                                   text="{0}/{1}".format(self.count,CAP),
                                   fill="coral3")
        elif self.count > int(0.75*CAP):
            self.draw_gradient(offset+int(round(total_length*self.count/float(CAP))),
                               self.p_height,
                               "#faaf3f",
                               "sienna",offset)
            self.canvas.itemconfig(self.counter,
                                   text="{0}/{1}".format(self.count,CAP),
                                   fill="#faaf3f")
        else:
            self.draw_gradient(offset+int(round(total_length*self.count/float(CAP))),
                               self.p_height,
                               "royal blue",
                               "#0069a5",offset)
            self.canvas.itemconfig(self.counter,
                                   text="{0}/{1}".format(self.count,CAP),
                                   fill="#0069a5")

    def draw_gradient(self, width, height, color1, color2, offset):
        '''Draw the gradient'''
        limit = int(round(self.p_height/3.0))
        (r1,g1,b1) = self.progress.winfo_rgb(color1)
        (r2,g2,b2) = self.progress.winfo_rgb(color2)
        r_ratio = float(r2-r1) / limit
        g_ratio = float(g2-g1) / limit
        b_ratio = float(b2-b1) / limit

        thickness = 3
        for i in range(limit):
            y0 = i*thickness
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            color = "#%4.4x%4.4x%4.4x" % (nr,ng,nb)
            self.progress.create_line(offset,
                                      y0+offset+int(round(thickness/2.0)),
                                      width,
                                      y0+offset+int(round(thickness/2.0)),
                                      fill=color,
                                      width=thickness)

    def push_count(self):
        # Send new count to the "cloud" (dweet.io)
        # To monitor the data at dweet.io go to http://dweet.io/follow/gbpool-rpi
        # A freeboard dashboard has also been created to graphically display the
        # current count and other information at https://freeboard.io/board/v0QMfs
        # This method is initially called from __init__ at the end, and this method
        # schedules itself to be called again in 2 seconds

        '''
        # create some fake count data
        # NOTE: this is overwriting self.count for testing purposes
        fake_count_inc = random.randint(-8,8)
        self.count = self.count + fake_count_inc
        if self.count <= 0:
            self.count = 0
        elif self.count > 248:
            self.count = 248
        # pretend the count was changed through the key_callback method
        # so the local display is updated
        self.key_callback(None)

        # create a fake open/close status
        status=random.choice(["Open"] * 10 + ["Closed"])
        if status =="Closed":
            reopen_time = (datetime.now() + timedelta(minutes=20)).strftime("%H:%M")
        else:
            reopen_time="--:--"
        '''

        date_updated=datetime.now().strftime("%a,%d %b")
        time_updated=datetime.now().strftime("%I:%M:%S %p").lstrip("0")
        '''
        payload = {"count":str(self.count),
                   "date_updated":date_updated,
                   "time_updated":time_updated,
                   "status":self.status_text,
                   "reopon_time":self.reopen_time_text,
                   "water_temp":self.main_temp_text}
        p1 = Process(name="dweet", target=self.dweet, args=(payload,))
        '''
        if self.reopen_time_text == "":
            reopen_time_text = "--:--"
        else:
            reopen_time_text = self.reopen_time_text

        time_date_updated = f'{time_updated} ({date_updated})'
        aio_payload = {'feeds': [{'key': 'count', 'value': self.count},
                                 {'key': 'status', 'value': self.status_text},
                                 {'key': 'reopen-time', 'value': reopen_time_text},
                                 {'key': 'time-updated', 'value': time_date_updated}]}
        p1 = Process(name="adafruit_io", target=self.adafruit_io, args=(aio_payload,))
        p1.daemon = True
        p1.start()

        # call this method again in 8 seconds
        self.master.after(8*1000, self.push_count)

    def dweet(self, payload):
        # dweet.io
        try:
            my_thing_name = os.environ["DWEET_THING_NAME"]
        except KeyError:
            return
        url = "https://dweet.io/dweet/for/" + my_thing_name
        try:
            rqs = requests.get(url, params=payload)
        except:
            pass
        sys.exit()

    def adafruit_io(self, payload):
        try:
            aio_username = os.environ['IO_USERNAME']
            aio_key = os.environ['IO_KEY']
        except KeyError:
            return
        group_name = 'pooldata'
        url = f'https://io.adafruit.com/api/v2/{aio_username}/groups/{group_name}/data'
        headers = {'X-AIO-KEY': aio_key, 'content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, json=payload)
        except:
            pass
        sys.exit()
 

def main():
    log_dir = os.path.expanduser("~/logs/")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    out_err = open(log_dir+"std_out_err.txt", "w")
    sys.stdout = sys.stderr = out_err

    parser = argparse.ArgumentParser()
    parser.add_argument("--fullscreen",
                        help="display fullscreen",
                        action="store_true",
                        default=False)
    args = parser.parse_args()

    root = tk.Tk()
    root.wm_title("Dashboard")

    if args.fullscreen:
        # discover screen resolution
        # can use shell command "fbset -s"
        # 1080p TV's appear to return (1824x1016) when using:
        #   overscan_left   = 0
        #   overscan_right  = 0
        #   overscan_top    = 0
        #   overscan_bottom = 0
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        root.attributes('-fullscreen', args.fullscreen)
    else:
        screen_w = 800  # 800  1824
        screen_h = 480  # 480  1016

    screen_dimensions = "%sx%s" % (screen_w, screen_h)

    root.resizable(width=False, height=False)
    root.geometry(screen_dimensions)

    scaled_font_size = int(round(screen_h*0.035))
    custom_font = tkFont.Font(family="Verdana", size=-scaled_font_size)
    root.option_add('*Font', custom_font)

    main_window = MainWindow(root, screen_dimensions)

    root.mainloop()

if __name__ == '__main__':
    main()

