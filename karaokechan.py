#! /usr/bin/env python2

import wx
import wx.media as wxm

import os.path
import user

import lyrics
import lyrics3v2

class LyricsCtrl(wx.TextCtrl):
    def __init__(self, parent, player):
        wx.TextCtrl.__init__(self, parent,
                             style = wx.TE_MULTILINE
                             | wx.TE_READONLY
                             | wx.TE_CENTRE)
        self.player = player
        self.lyrics = None
        self.phraseTimer = wx.Timer(self)
        self.lastPhrase = None
        self.Bind(wx.EVT_TIMER, self.HandlePhraseTimer, self.phraseTimer)
        parent.Bind(wxm.EVT_MEDIA_STATECHANGED, self.HandlePlayer, self.player)

    def SetLyrics(self, lyrics):
        self.lyrics = lyrics
        self.phrases = lyrics.getPhrases()
        self.times = lyrics.getTimes()
        self.SetValue(''.join(self.phrases))

    def CenterPosition(self, pos):
        boxHeight = self.GetClientSize()[1]
        lineHeight = self.GetDefaultStyle().GetFont().GetPixelSize().GetHeight()
        lineCount = boxHeight / lineHeight

        currentLine = self.PositionToXY(pos)[1]
        lastLine = self.PositionToXY(self.GetLastPosition())[1]

        # As long as lineCount is nonzero, (lineCount-1)/2 and
        # lineCount/2 must be two nonnegative numbers with sum
        # lineCount-1, so the number of lines from topLine to
        # bottomLine inclusive will be exactly lineCount.
        topLine = max(currentLine - (lineCount-1)/2, 0)
        bottomLine = min(currentLine + lineCount/2, lastLine)

        self.ShowPosition(self.XYToPosition(0, topLine))
        self.ShowPosition(self.XYToPosition(0, bottomLine))
        self.ShowPosition(pos) # even if something weird happens, pos will be visible

    def HandlePhraseTimer(self, evt):
        playTime = self.player.Tell() / 10
        phrase, startTime, endTime = self.lyrics.getCurrent(playTime)

        if phrase is not None:
            phraseStart = sum(len(p) for p in self.phrases[:phrase])
            phraseEnd = phraseStart + len(self.phrases[phrase])

            if self.lastPhrase is not None:
                self.SetStyle(self.lastPhrase[0], self.lastPhrase[1],
                              wx.TextAttr(wx.Colour(100,100,100)))

            self.SetStyle(phraseStart, phraseEnd, wx.TextAttr(wx.Colour(0, 0, 255)))
            self.CenterPosition(phraseStart)

            self.lastPhrase = (phraseStart, phraseEnd)

        if endTime is not None:
            self.phraseTimer.Start((endTime - playTime) * 10, wx.TIMER_ONE_SHOT)

    def HandlePlayer(self, evt):
        if self.player.GetState() == wxm.MEDIASTATE_PLAYING:
            self.HandlePhraseTimer(None)
        else:
            self.phraseTimer.Stop()

class KaraokePlayer(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        # media widget
        self.player = wxm.MediaCtrl(self)

        # lyrics viewer
        self.lyricsViewer = LyricsCtrl(self, self.player)

        # menu bar
        self.menuBar = wx.MenuBar()
        self.fileMenu = wx.Menu()
        self.fileMenu.Append(wx.ID_OPEN)
        self.fileMenu.Append(wx.ID_EXIT)
        self.menuBar.Append(self.fileMenu, "&File")
        self.SetMenuBar(self.menuBar)

        self.Bind(wx.EVT_MENU, self.HandleOpen, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.HandleExit, id=wx.ID_EXIT)

        # controls
        self.playPauseButton = wx.ToggleButton(self, label="Play/Pause")
        self.stopButton = wx.Button(self, label="Stop")
        self.muteButton = wx.ToggleButton(self, label="Mute")
        self.volumeSlider = wx.Slider(self, minValue=0, maxValue=100, size=(100, -1))
        self.timeSlider = wx.Slider(self, minValue=0, maxValue=0)

        self.Bind(wx.EVT_TOGGLEBUTTON, self.HandlePlayPause, self.playPauseButton)
        self.Bind(wx.EVT_BUTTON, self.HandleStop, self.stopButton)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.HandleMute, self.muteButton)
        self.Bind(wx.EVT_SLIDER, self.HandleVol, self.volumeSlider)
#        self.Bind(wx.EVT_SLIDER, self.HandleTime, self.timeSlider)

        # sizers
        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttonSizer.Add(self.playPauseButton, 0, wx.ALL, 10)
        self.buttonSizer.Add(self.stopButton, 0, wx.ALL, 10)
        self.buttonSizer.Add(self.muteButton, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        self.buttonSizer.Add(self.volumeSlider, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        self.controlSizer = wx.BoxSizer(wx.VERTICAL)
        self.controlSizer.Add(self.timeSlider, 0, wx.EXPAND)
        self.controlSizer.Add(self.buttonSizer, 0)

        self.viewerSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.viewerSizer.Add(self.player, 1, wx.EXPAND)
        self.viewerSizer.Add(self.lyricsViewer, 1, wx.EXPAND)

        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.mainSizer.Add(self.viewerSizer, 1, wx.EXPAND)
        self.mainSizer.Add(self.controlSizer, 0, wx.EXPAND)

        self.SetSizerAndFit(self.mainSizer)

        # timer
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.HandleTimer, self.timer)

        self.Show()

    def HandleOpen(self, evt):
        self.HandleStop(None)

        dialog = wx.FileDialog(self)

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            filename = dialog.GetFilename()

            # Show lyrics, if available
            if os.path.splitext(filename)[1] == ".mp3":
                try:
                    self.lyricsViewer.SetLyrics(lyrics3v2.load(lyrics3v2.read(filepath)))
                except ValueError:
                    pass

            self.player.Load(filepath)

            # Hide lyrics viewer if there are no lyrics
            if self.lyricsViewer.IsEmpty():
                self.viewerSizer.Hide(self.lyricsViewer)
            else:
                self.viewerSizer.Show(self.lyricsViewer)

            # Hide player screen if there's no video
            if self.player.GetBestSize() == (0,0):
                self.viewerSizer.Hide(self.player)
            else:
                self.viewerSizer.Show(self.player)

            self.viewerSizer.Layout()

            title = filename
            self.SetTitle(u'{} - Karaoke-chan'.format(title))

            self.volumeSlider.SetValue(int(self.player.GetVolume() * 100))

    def HandleExit(self, evt):
        self.player.Stop()
        self.Close()

    def HandlePlayPause(self, evt):
        if self.playPauseButton.GetValue():
            self.player.Play()
            self.timer.Start(milliseconds=500)
        else:
            self.player.Pause()
            self.timer.Stop()

    def HandleStop(self, evt):
        self.timer.Stop()
        self.player.Stop()
        self.timeSlider.SetMax(0)
        self.timeSlider.SetValue(0)
        self.playPauseButton.SetValue(False)
        self.lyricsViewer.Clear()

    def HandleMute(self, evt):
        if self.muteButton.GetValue():
            self.player.SetVolume(0)
        else:
            self.player.SetVolume(self.volumeSlider.GetValue() / 100.0)

    def HandleVol(self, evt):
        self.player.SetVolume(self.volumeSlider.GetValue() / 100.0)

    def HandleTimer(self, evt):
        self.timeSlider.SetMax(self.player.Length() / 1000)
        self.timeSlider.SetValue(self.player.Tell() / 1000)


if __name__ == "__main__":
    app = wx.App(False)
    player = KaraokePlayer(None, title="Karaoke-chan")
    player.Show()
    app.MainLoop()
