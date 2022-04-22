# -*- coding: utf-8 -*-
"""archon_analyze.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1A1AEVWbrBRvxWBlDTrvvYClTazBz5ylV
"""

from google.colab import drive
drive.mount('/content/drive')

!pip install librosa==0.8.0
import numpy as np
import json as json
import pandas as pd
import matplotlib.pyplot as plt
import librosa
import math
import os, os.path

destination_db = "/content/drive/My Drive/IRCMS_GAN_collaborative_database/Experiments/colab-violingan/archon-analysis/" #@param {type:"string"}
dest_datasize = "46676" #@param {type:"string"}
slice_size = "2" #@param {type:"string"}
hop_length = "2048" #@param {type:"string"}
sr = "44100" #@param {type:"string"}
output_filename = "/content/drive/My Drive/analysis_f.json" #@param {type:"string"}

hop = int(hop_length)
sr = int(sr)
slice_size = int(slice_size)
dest_datasize = int(dest_datasize)
counter = 0
data = []

dest_datasize = len(
    [name for name in os.listdir(destination_db) if os.path.isfile(
        os.path.join(destination_db, name))])
# NOTE: depending on size of folder, this can error out multiple times - 
#Colab will cache the results, so retry until success and log the number for future attempts.
print(dest_datasize)

counter = 0
pcounter = 0
ncounter = 0

data = []
for filename in os.scandir(destination_db):

  if (filename.path.endswith(".wav")):

    y, sr = librosa.load(filename, sr=sr)
    
    id = filename.name

    cent = np.median(
        np.ndarray.flatten(
        librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop)))
    flat = np.median(
        np.ndarray.flatten(
        librosa.feature.spectral_flatness(y=y, hop_length=hop)))
    rolloff = np.median(
        np.ndarray.flatten(
        librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop)))
    rms = np.median(
        np.ndarray.flatten(
        librosa.feature.rms(y=y, hop_length=hop)))
    
    f0, voiced_flag, voiced_probs = librosa.pyin(y,
                                   fmin=librosa.note_to_hz('C2'),
                                   fmax=librosa.note_to_hz('C7'))
    
    voiced = np.median(np.ndarray.flatten(voiced_flag))

    if (voiced == True):
      f0 = f0[~np.isnan(f0)]
      pitch = np.median(np.ndarray.flatten(f0))
      pitch = str(librosa.hz_to_note(pitch))
      pitch = pitch.replace("♯", "#") 
      pcounter += 1
    else: 
      pitch = "unpitched"
      ncounter += 1
  
    data.append({
        str(id):
        { 
            "cent": str(cent),
            "flat": str(flat),
            "rolloff": str(rolloff),
            "rms": str(rms),
            "pitch": pitch
        }
    })

    counter += 1
    
    if (counter % 1000 == 0): 
      print("completed " + str(counter) + " of " + str(dest_datasize))
      print ("there are " + str(pcounter) + " pitched elements and " + str(ncounter) + " nonpitched elements.")

## stores array of nested dicts as json
savefile = output_filename
with open(savefile, 'a') as outfile:
  json.dump(data, outfile, indent=2)

## returns json as array of nested dicts
f = open(output_filename)
d_lib = json.load(f)

def sort_by_pitch (unsort_or_sort, json_file):

  counter = 0 
  pitch = ""
  
  for entry in json_file:

    for k, v in entry.items():
      sample = v
      counter += 1
      print(counter)


      filename = k
      print(destination_db + filename)

      for k2, v2 in sample.items():

        if (k2 == "pitch"): 
          pitch = v2

          if (pitch != "unpitched"): 
            oct = int(pitch[-1])
            pitch = pitch.replace(str(oct), "")  
        
      pitch_dir = destination_db + pitch + "/"   

      if (unsort_or_sort == "sort"):     
        if (os.path.exists(pitch_dir) == False): os.makedirs(pitch_dir)
        os.replace(destination_db + filename, pitch_dir + filename)

      else: 
        os.replace(pitch_dir + filename, destination_db + filename)

sort_by_pitch ("sort", d_lib)

#Collect Stats
counter = 0
c_buff, f_buff, v_buff, o_buff, p_buff, r_buff = [], [], [], [], [], [] #very simply just collecting base descriptor info
uc_buff, uf_buff, pc_buff, pf_buff, pr_buff, ur_buff = [], [], [], [], [], [] #added here just to contrast pitched vs unpitched

for entry in d_lib:
  for k, v in entry.items():
    sample = v
    counter += 1
    filename = k

    for k2, v2 in sample.items():
      if (k2 == "cent"): 
        c_buff.append(float(v2))
      if (k2 == "flat"): 
        f_buff.append(float(v2))
      if (k2 == "rms"):
        v_buff.append(float(v2))
      if (k2 == "rolloff"):
        r_buff.append(float(v2))
      if (k2 == "pitch"):
        if (v2 != "unpitched"):
          o_buff.append(v2)
          p_buff.append(v2[:-1])

          for k2, v2 in sample.items():
            if (k2 == "cent"): pc_buff.append(float(v2))
            if (k2 == "flat"): pf_buff.append(float(v2))
            if (k2 == "rolloff"): pr_buff.append(float(v2))

        else:
          p_buff.append(v2)

          for k2, v2 in sample.items():
            if (k2 == "cent"): uc_buff.append(float(v2))
            if (k2 == "flat"): uf_buff.append(float(v2))
            if (k2 == "rolloff"): ur_buff.append(float(v2))

def histogram(metric, min, max, title):
  plt.rcParams["figure.figsize"] = [17.50, 11]
  plt.rcParams["figure.autolayout"] = True

  print("starting graph")
  x = np.sort(np.array(metric))
  HIST_BINS = np.linspace(min, max, 100)

  plt.title((title + " Distribution"))
  n = plt.hist(x, HIST_BINS)
 
  plt.xlabel(title)
  plt.ylabel('Magnitude')

  plt.show()

histogram(pc_buff, 0, 10000, "Centroid")
#pitched < 4k, peak around 2.2k
#unpitched >2.2k, peak around 3.2k, goes until 8k or so

histogram(pf_buff, 0, 0.1, "Flatness")
## unpitched flatness is much greater generally than pitched flatness

histogram(ur_buff, 0, 18000, "Rolloff")
#pitched < 7.5k generally, peak around 4-5k
# unpitched 4k-15k, peaks throughout, much of the center of gravity between 4k and 12.5k

histogram(v_buff, 0, 0.5, "RMS")

x = pd.Series(p_buff).value_counts()
x.plot(kind='bar')
## most information is nonpitched, though about 1/6th of the elements are pitched

x = pd.Series(o_buff).value_counts()
x.plot(kind='bar')
## most of the pitched information is in octaves 3-4, the vast majority between A3 and B3.