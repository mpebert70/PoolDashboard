#!/bin/bash

# need to force the environment variables to be defined for cron
source /etc/profile.d/pool_dashboard.sh

# change directory to the log dir (/home/guard/logs)
cd /home/guard/logs

# run the gnuplot script to generate the end-of-day plot
gnuplot -e "date='$(date +%m)/$(date +%d)/$(date +%y)'" -e "outfile='Facility_Load_$(date +%B)_$(date +%d)_$(date +%Y).png'" /home/pi/programs/pool_dashboard/scripts/load.plt

# email the plot to everyone who wants it
emails=$(echo $PLOT_EMAILS | tr ";" "\n")
for addr in $emails
do
    mpack -s "Today's Facility Load Plot" Facility_Load_$(date +%B)_$(date +%d)_$(date +%Y).png $addr
done

# delete the plot
rm Facility_Load_$(date +%B)_$(date +%d)_$(date +%Y).png

# email the log files
emails=$(echo $LOG_EMAILS | tr ";" "\n")
for addr in $emails
do
    mpack -s "Facility Time History Log" facility_time_hist_$(date +%Y).csv $addr
    mpack -s "Facility Event Log" facility_event_log_$(date +%Y).csv $addr
done

