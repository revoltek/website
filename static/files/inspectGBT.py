#!/usr/bin/python

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# inspectGBT Version 1.0
# Author: Francesco de Gasperin (astro@voo.it)

# Program to interactively plot GBT data organized in Obit fits format

import sys, os
import pyfits
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as clr
from matplotlib.widgets import Cursor, Button, RadioButtons, CheckButtons, Slider
from mpl_toolkits.axes_grid1 import make_axes_locatable # for decent colorbar

plt.rcParams['font.size']=12

class viewer_2d(object):
    def __init__(self, valON, valOFF, scans, RAs, DECs, time=None, freq=None):
        """
        Shows a given array in a 2d-viewer.
        Input: z, an 2d array.
        x,y coordinters are optional.
        """

        self.valON = valON
        self.valOFF = valOFF
        self.scans = scans
        self.RAs = RAs
        self.DECs = DECs
        self.z = np.zeros(shape = valON.shape[1:]) # to inizialize the overview

        if time == None:
            self.alltime = np.arange(self.valON.shape[1])
        else:
            self.alltime = time

        if freq == None:
            self.allfreq = np.arange(self.valON.shape[2])
        else:
            self.allfreq = freq

        self.fig = plt.figure()

        # Set parameters for initial overview
        self.pol = 0 # XX is the default
        self.cal = 'diff' # ON-OFF is the default
        self.fft_time = False
        self.fft_freq = False
        self.log_time = False
        self.log_freq = False
        self.time = self.alltime
        self.freq = self.allfreq

        # scan slide (select the first plotted scan and how many scans)
        slide_ax1 = plt.subplot2grid((20,20),(19,13),rowspan=1,colspan=3)
        slide_ax2 = plt.subplot2grid((20,20),(19,17),rowspan=1,colspan=3)
        self.slide_beg_scan = Slider(slide_ax1, 'From', min(self.scans), max(self.scans), valinit=min(self.scans),  valfmt='%1i')
        self.slide_end_scan = Slider(slide_ax2, 'To', min(self.scans), max(self.scans), valinit=max(self.scans), valfmt='%1i')
        self.slide_beg_scan.slidermax = self.slide_end_scan
        self.slide_end_scan.slidermin = self.slide_beg_scan

        # Doing some layout with subplots:
        self.fig.subplots_adjust(0.05,0.05,0.98,0.98,0.1)
        self.overview = plt.subplot2grid((20,20),(0,0),rowspan=20,colspan=10)
        self.overview.set_xlabel('Channel')
        self.overview.set_ylabel('Sample')
        divider = make_axes_locatable(self.overview)
        self.cax = divider.append_axes("bottom", "3%", pad="5%")
        # creating overview image
        self.overview_im = self.overview.imshow(self.z, interpolation='nearest', aspect='auto')
        self.draw_overview()
        # time/freq subplots
        self.time_subplot = plt.subplot2grid((20,20),(0,11),rowspan=9,colspan=8)
        self.freq_subplot = plt.subplot2grid((20,20),(10,11),rowspan=9,colspan=8)

        #Adding widgets, to not be garbage-collected they are put in a list:
        # cursor for selecting time/freq
        cursor = Cursor(self.overview, useblit=True, color='black', linewidth=2 )
        # reset button
        but_ax = plt.subplot2grid((20,20),(15,19),rowspan=1,colspan=1)
        reset_button = Button(but_ax,'Reset')
        # legend button
        but_ax2 = plt.subplot2grid((20,20),(16,19),rowspan=1,colspan=1)
        legend_button = Button(but_ax2,'Legend')
        # point button
        but_ax3 = plt.subplot2grid((20,20),(17,19),rowspan=1,colspan=1)
        point_button = Button(but_ax3,'Pointings')
        # quit button
        but_ax4 = plt.subplot2grid((20,20),(18,19),rowspan=1,colspan=1)
        quit_button = Button(but_ax4,'Quit')
        # polarizaitions radio buttons
        butpol_ax = plt.subplot2grid((20,20),(0,19),rowspan=2,colspan=1)
        pol_selector = RadioButtons(butpol_ax, labels=['XX','YY','XY','YX'], active=0, activecolor='black')
        # ON/OFF/diff button
        butcal_ax = plt.subplot2grid((20,20),(2,19),rowspan=2,colspan=1)
        cal_selector = RadioButtons(butcal_ax, labels=['diff','ON','OFF'], active=0, activecolor='black')
        # fft buttons
        butfft_ax1 = plt.subplot2grid((20,20),(9,11),rowspan=1,colspan=1)
        butfft_ax2 = plt.subplot2grid((20,20),(19,11),rowspan=1,colspan=1)
        fft_time_switch = CheckButtons(butfft_ax1, ['Time FFT'], [False])
        fft_freq_switch = CheckButtons(butfft_ax2, ['Freq FFT'], [False])
        # log buttons
        butlog_ax1 = plt.subplot2grid((20,20),(9,12),rowspan=1,colspan=1)
        butlog_ax2 = plt.subplot2grid((20,20),(19,12),rowspan=1,colspan=1)
        log_time_switch = CheckButtons(butlog_ax1, ['Time log'], [False])
        log_freq_switch = CheckButtons(butlog_ax2, ['Freq log'], [False])

        self._widgets = [cursor,reset_button,legend_button,point_button,quit_button,pol_selector,fft_time_switch,
            fft_freq_switch,cal_selector,log_time_switch,log_freq_switch]

        #connect events
        reset_button.on_clicked(self.reset_plots)
        legend_button.on_clicked(self.show_legend)
        point_button.on_clicked(self.show_point)
        quit_button.on_clicked(self.quit)
        pol_selector.on_clicked(self.select_pol)
        cal_selector.on_clicked(self.select_cal)
        fft_time_switch.on_clicked(self.fft_data)
        fft_freq_switch.on_clicked(self.fft_data)
        log_time_switch.on_clicked(self.log_data)
        log_freq_switch.on_clicked(self.log_data)
        self.fig.canvas.mpl_connect('button_press_event',self.click)

    def quit(self, event):
        """Kill all windows open"""
        print "Done."
        plt.close('all')


    def get_time_idx(self):
        """Get time index based on slide selection"""
        beg_scan = self.slide_beg_scan.val
        end_scan = self.slide_end_scan.val
        idx1 = np.where(self.scans >= beg_scan)[0]
        idx2 = np.where(self.scans <= end_scan)[0]
        return list(set(idx1) & set(idx2))


    def draw_overview(self):
        """Draw the main plot"""
        idx = self.get_time_idx()
        self.time = self.alltime[idx]
        if self.cal == 'ON': self.z = self.valON[self.pol][idx]
        if self.cal == 'OFF': self.z = self.valOFF[self.pol][idx]
        if self.cal == 'diff': self.z = self.valON[self.pol][idx] - self.valOFF[self.pol][idx]
        self.overview.set_title('cal: '+str(self.cal)+' - pol: '+str(self.pol))
        self.overview_im.set_data(self.z)
        if np.amin(self.z) > 0:
            self.overview_im.set_norm(clr.LogNorm(vmin=np.amin(self.z), vmax=np.amax(self.z)))
        else:
            self.overview_im.set_norm(clr.Normalize(vmin=-np.std(self.z), vmax=np.std(self.z)))
        self.overview_im.set_extent([np.amin(self.freq),np.amax(self.freq),np.amin(self.time),np.amax(self.time)])
        plt.colorbar(self.overview_im, cax=self.cax, orientation='horizontal')


    def draw_subplot_time(self, x, y, label):
        """Draw a subplot content"""

        if self.fft_time:
            y = abs(np.fft.rfft(y))
            x = range(len(y))

        if self.log_time:
            self.time_subplot.set_yscale('log')
            y = abs(y)
        else:
            self.time_subplot.set_yscale('linear')

        c = self.time_subplot.plot(x, y, label = label)
        self.time_subplot.relim()
        self.time_subplot.autoscale_view()
        return c


    def draw_subplot_freq(self, x, y, label):
        """Draw a subplot content"""

        if self.fft_freq:
            y = abs(np.fft.rfft(y))
            x = range(len(y))

        if self.log_freq:
            self.freq_subplot.set_yscale('log')
            y = abs(y)
        else:
            self.freq_subplot.set_yscale('linear')

        c = self.freq_subplot.plot(x, y, label = label)
        self.freq_subplot.relim()
        self.freq_subplot.autoscale_view()
        return c


    def show_legend(self, event):
        """Shows legend for the plots"""
        for pl in [self.time_subplot,self.freq_subplot]:
            if len(pl.lines)>0:
                pl.legend()
        plt.draw()


    def show_point(self, event):
        """Shows pointings in another plot"""
        timeidx = self.get_time_idx()
        self.fig2 = plt.figure()
        ax = self.fig2.add_subplot(111)
        ax.set_title('Pointings')
        ax.set_xlabel('RA [deg]')
        ax.set_ylabel('DEC [deg]')
        scansidx = [[i for i, x in enumerate(self.scans[timeidx]) if x == y] for y in np.unique(self.scans[timeidx])]
        for scanidx in scansidx:
            ax.plot(self.RAs[timeidx][scanidx], self.DECs[timeidx][scanidx], marker='o')
        self.fig2.show()


    def reset_plots(self, event=None, plot=None):
        """Clears the subplots."""
        if plot == None: plots = [self.time_subplot,self.freq_subplot,self.overview]
        if plot == 'time': plots = [self.time_subplot]
        if plot == 'freq': plots = [self.freq_subplot]
        for j in plots:
            j.lines=[]
            j.legend_ = None
        plt.draw()
        self.draw_overview()


    def fft_data(self, axis):
        """Set the FFT in one of the two plots"""
        if axis == 'Time FFT':
            self.fft_time = not self.fft_time
            self.reset_plots('change fft', 'time')
        if axis == 'Freq FFT':
            self.fft_freq = not self.fft_freq
            self.reset_plots('change fft', 'freq')


    def log_data(self, axis):
        """Set the Log-scale in one of the two plots"""
        if axis == 'Time log':
            self.log_time = not self.log_time
            self.reset_plots(plot='time')
        if axis == 'Freq log':
            self.log_freq = not self.log_freq
            self.reset_plots(plot='freq')


    def select_pol(self, pol):
        """Change the displayed polarization."""
        self.pol = {'XX':0,'YY':1,'XY':2,'YX':3}[pol]
        self.reset_plots()
        self.draw_overview()


    def select_cal(self, cal):
        """Change the displayed polarization."""
        self.cal = cal
        self.reset_plots()
        self.draw_overview()


    def click(self,event):
        """
        What to do, if a click on the figure happens:
            1. Check which axis
            2. Get data coord's.
            3. Plot resulting data.
            4. Update Figure
        """
        if event.inaxes==self.overview:
            # Get nearest data
            freqpos = np.argmin(np.abs(event.xdata-self.freq))
            timepos = np.argmin(np.abs(event.ydata-self.time))

            # Check which mouse button (1: left, 2: central, 3: right):
            if event.button == 1 or event.button == 2:
                c, = self.draw_subplot_freq(self.freq, self.z[timepos,:], label=str(self.time[timepos]))
                self.overview.axhline(self.time[timepos],color=c.get_color(), lw=2)

            if event.button == 3 or event.button == 2:
                c, = self.draw_subplot_time(self.time, self.z[:,freqpos], label=str(self.freq[freqpos]))
                self.overview.axvline(self.freq[freqpos],color=c.get_color(), lw=2)

        # Click on onlt subplot will activate the other
        if event.inaxes == self.freq_subplot:
            freqpos = np.argmin(np.abs(event.xdata-self.freq))
            c, = self.draw_subplot_time(self.time, self.z[:,freqpos],label=str(self.freq[freqpos]))
        #    self.overview.axhline(self.freq[freqpos],color=c.get_color(), lw=2)

        if event.inaxes == self.time_subplot:
            timepos = np.argmin(np.abs(event.xdata-self.time))
            c, = self.draw_subplot_freq(self.freq, self.z[timepos,:], label=str(self.time[timepos]))
        #    self.overview.axvline(self.time[timepos],color=c.get_color(), lw=2)

        #Show it
        plt.draw()

if __name__=='__main__':

    if len(sys.argv) != 2:
        print "Usage: inspectGBT.py filename.fits"
        sys.exit(0)

    try:
        fitsfile = pyfits.open(sys.argv[1])
    except:
        print "ERROR opening the fits file."
        sys.exit(1)

    datatab = fitsfile[4]

    maskcal = datatab.data.field('CAL') == 1

    dataON = datatab.data[maskcal].field('DATA')
    dataOFF = datatab.data[~maskcal].field('DATA')

    scans = datatab.data.field('SCAN')[maskcal]
    RAs = datatab.data.field('RA')[maskcal]
    DECs = datatab.data.field('DEC')[maskcal]

    dataON = np.rollaxis(dataON, 1)[0] # move+remove feed
    dataON = np.rollaxis(dataON, 3)[0] # move+remove weigth
    dataON = np.rollaxis(dataON, 2) # move pol

    dataOFF = np.rollaxis(dataOFF, 1)[0] # move+remove feed
    dataOFF = np.rollaxis(dataOFF, 3)[0] # move+remove weigth
    dataOFF = np.rollaxis(dataOFF, 2) # move pol

    #Put it in the viewer
    inspector = viewer_2d(dataON, dataOFF, scans, RAs, DECs)
    #Show it
    plt.show()
