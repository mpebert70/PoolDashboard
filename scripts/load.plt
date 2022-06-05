set terminal png font "sans, 14" size 1000,400
set output outfile
set datafile separator ","
set key autotitle columnhead
set xdata time
set format x "%H:%M"
set timefmt "%m/%d/%y %H:%M"
set xrange [date." 10:00" : date." 22:00"]
set xtics rotate 60 3600
set yrange [0:250]
set grid ytics
set title date font "sans, 18"
set style fill solid
set boxwidth 500
set y2range [60:110]
set ytics 50 nomirror
set y2tics 10 nomirror
set ylabel "Facility Load"
set y2label "Temperature (\260F)"
year = strftime("%Y", time(0))
plot "/home/guard/logs/facility_time_hist_".year.".csv" u 1:2 w boxes linecolor rgb "red" title "Facility Load" axes x1y1, "/home/guard/logs/facility_time_hist_".year.".csv" u 1:12 w line lw 2 linecolor rgb "web-green" title "Air Temp" axes x1y2, "/home/guard/logs/facility_time_hist_".year.".csv" u 1:10 w line lw 2 linecolor rgb "web-blue" title "Water Temp" axes x1y2
