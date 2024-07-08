
# -*- coding: utf-8 -*-
"""
"""


from spotpy.parameter import Uniform
from spotpy.objectivefunctions import rmse, mae, mse
import spotpy
import os
import json
import sys
#import matplotlib.pyplot as plt
import pandas as pd
import csv

import numpy as np

from ext_call import run_monica_batch

from datetime import datetime, timedelta

# Lib to crate matrix from csv and calculate the
 
#from csv_to_matrix import csv_matrix   # TODO - objective function penalized by gradient

from copy import deepcopy
import time


start_time = time.time()


# Path to all files
path = r"D:\_Trabalho\_Publicacoes_nossas\Inv_Mod_SHP\__MONICA_New\_Boo_Monica\input_files" + os.sep

exe = r"_monica-run.exe"
env_path = r"D:\_Trabalho\_Publicacoes_nossas\Inv_Mod_SHP\__MONICA_New\_Boo_Monica\input_files\monica-parameters" + os.sep
meta_file = r"_meta_organizer.csv"




# Ground Truth data 
res_obs_obj = pd.read_csv(r"D:\_Trabalho\_Publicacoes_nossas\Inv_Mod_SHP\__MONICA_New\_Boo_Monica\input_files\raw_data\yield.csv")["Yield_kg_per_ha"]
res_obs_obj = res_obs_obj.values   # todos os dados sendo lidos


# Base weather file
base_weather_file = r"D:\_Trabalho\_Publicacoes_nossas\Inv_Mod_SHP\__MONICA_New\_Boo_Monica\109_120_boo-2019-21.csv"

# Weather rain header in file
weather_header = "precip"
weather_sep =","
weight_rain = 100  # Weight to force the rain sum to be the same value as measured


## TARGET outputs header name. It will return the maximum value of the column.
out_head = "Yield"


path_cultivar = r"D:\_Trabalho\_Publicacoes_nossas\Inv_Mod_SHP\__MONICA_New\_Boo_Monica\input_files\monica-parameters\crops\triticale" + os.sep
file_cultivar = r"winter-triticale_mod.json"

# Spotpy parameter
rep = 40



class spot_setup(object):
    def __init__(self, obj_func=None):
        
        self.path = path
        self.exe  = exe
        
        self.full_cultivar = path_cultivar + file_cultivar
        
        self.meta_file = meta_file
        self.env_path = env_path
        os.environ["MONICA_PARAMETERS"] = self.env_path
        
        self.obj_func = obj_func
        
        
        self.trueObs = res_obs_obj
        
        # One time loaded methods
        
        self.out_f_names, self.weather_files = self._extract_outfiles_from_meta(f"{self.path}{self.meta_file}")
        
        
        # read initial water data and store it in a matrix
        # weather header
        self.base_weather_file = base_weather_file
        self.weather_h = weather_header
        self.weather_sep = weather_sep
        self.ini_weather_data = self.read_rain()  # initial weather data file as pandas, used as TEMPLATE and other constants
        self.temp_weather_data = deepcopy(self.ini_weather_data)
        self.param_temp = np.zeros(len(self.weather_files))
        self.weight_rain = weight_rain
        
        # TO DO get the number of pixels in order and iterate for smoothed version
        
        self.params=[]
        # Initializing the parameters
        for i in range(len(self.weather_files)):
            self.params.append(Uniform(f"rain_{i}", low=0.3, high=1.7, optguess=1.))
        print("Number of parameters to be adjusted:", len(self.params))
        print("init done")
        
        
        
    # method to extract the output file names from the meta file
    def _extract_outfiles_from_meta(self, csv_file_path):
        sim_file_list = []
        weather_fs = []
        with open(csv_file_path, 'r') as f:
            csv_reader = csv.reader(f)
            header = next(csv_reader)
            sim_file_index = header.index("out_file")
            weth_file_index = header.index("weather_file")
            for row in csv_reader:
                sim_file_list.append(row[sim_file_index])
                weather_fs.append(row[weth_file_index])
        return sim_file_list, weather_fs
    
    
    
    def parameters(self):
        return spotpy.parameter.generate(self.params)
    
    
    
    def read_rain(self):
        # Read and stores the initially weather data content (whole file)
        rain = pd.read_csv(self.base_weather_file, sep=self.weather_sep)
        return rain
    
    
    
    def write_rain(self, param_weather):
        for i in range(len(param_weather)):
            # save into a temporary weather data
            self.temp_weather_data[self.weather_h] = self.ini_weather_data[self.weather_h] * round(param_weather[i],2)
            file_path = self.weather_files[i]
            self.temp_weather_data.to_csv(file_path, sep=self.weather_sep, index=False)
        return None
    
    
    
    def simulation(self, x):
        """
        vector x are the generated parameters
        """
        
        # generate and save weather files
        self.write_rain(x)
        
        # run MONICA
        run_monica_batch(self.path, self.exe, self.meta_file, self.env_path)
        
        # read results   ######################################################################
        # indexes and columns
        result_field = []
        for ii in self.out_f_names:
            
            fils_name = f"{self.path}{ii}"
            
            out_ = pd.read_csv(fils_name, skiprows=1)["Yield"].max()
            resul_ = np.array(out_, dtype=float)
            
            
            ######################################## CHANGE HERE FOR different results analysis 
            
            result_field.append(resul_)
        
        
        return np.array(result_field), np.array(x)
    
    
    
    def evaluation(self):
        
        # READ true yield here !!!
        
        return self.trueObs
    
    
    
    def objectivefunction(self, simulation, evaluation, params=None):
        #SPOTPY expects to get one or multiple values back, 
        #that define the performance of the model run
        
        
        #######################################   OBJECTIVE FUNCTION pt2 HERE !!!
        
        
        sim_data, par_temp = simulation
        
        # Average in the rain modifiers
        aver = sum(par_temp)/len(par_temp)
        weather_weight_temp = (abs(aver - 1) * self.weight_rain)**2
        
        # rmse, mse, mae  ->  options
        like = rmse(evaluation , sim_data) + weather_weight_temp
        #print("MAE func: ",round(like, 2), "  weather weight compoent:",round( weather_weight_temp , 2))
        
        return like



print("Starting setup")
print("--- %s seconds ---" % (time.time() - start_time))
_setup = spot_setup()


print("starting spotpy")
print("--- %s seconds ---" % (time.time() - start_time))
sampler = spotpy.algorithms.sceua(_setup, dbname='test_SCEUA_MONICA', dbformat='csv')


print("starting sampler")
print("--- %s seconds ---" % (time.time() - start_time))
sampler.sample(repetitions = rep, ngs=10, kstop=3, peps=0.01, pcento=0.01)


print("Reading results")
print("--- %s seconds ---" % (time.time() - start_time))
results = spotpy.analyser.load_csv_results('test_SCEUA_MONICA')




sys.exit()










