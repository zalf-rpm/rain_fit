
# -*- coding: utf-8 -*-


"""

Generate MOONICA files to fit rainn values

"""


import os
import sys

import pandas as pd
from copy import deepcopy

import json
import shutil



class write_files:
    def __init__(self, path_soil_weather_data, file_soil, field, dens, path_all_out, weather_file, start_date, end_date, template_sim, template_soil):
        
        
        self.path_soil_data = path_soil_weather_data    # path
        self.file_soil = file_soil   # file name
        self.ful_f = f"{self.path_soil_data}{self.file_soil}"
        
        self.path_all_out = path_all_out
        
        self.field = field
        self.dens = dens
        
        # Weather
        self.weather = weather_file
        self.csv_separator = csv_separator
        
        self.start_date = start_date
        self.end_date   = end_date
        
        # use pandas to read CSV file
        self.df = pd.read_csv(self.ful_f)
        #filter the data to the selected parameters
        #self.df_filter = self.df[(self.df["Field_name"] == self.field) & (self.df["compaction_level"] == self.dens)]  #  not bgood for Boo
        
        self.df_filter = deepcopy(self.df)  #  remove for Erik's data
        self.df_filter.loc[:, "Thickness"] = self.df_filter["Lower_depth"] - self.df_filter["Upper_depth"]
        
        # sorting based on point then layer
        self.df_filter = self.df_filter.sort_values(by=['Field_Profile_number', 'Horizon_number'])
        
        # grabbing data
        self.lay_thic = self.df_filter["Thickness"]
        self.soc = self.df_filter["SOC"]
        self.BD  = self.df_filter["BD"] * 1000.0  # from g/cm3 to kg/m3
        
        # texture
        self.tex = self.df_filter["KA5"]
        self.sand = self.df_filter["SAND"] / 100.0  # transform from 0 to 1
        self.clay = self.df_filter["CLAY"] / 100.0
        
        # get the field point IDs
        self.point_ID = self.df_filter["Field_Profile_number"]
        self.val_uniq = self.point_ID.unique()
        
        # self.val_uniq carries the number of simulations per batch
        
        # load templates for soil and sim files
        with open(os.path.join(self.path_soil_data , template_sim)) as f:
            self.sim_template = json.load(f)
        with open(os.path.join(self.path_soil_data , template_soil)) as f:
            self.soil_template = json.load(f)
        
        
        # meta
        self.BU_sim_files = []
        self.BU_site_names = []
        self.BU_out_files = []
        self.point_ID_log = []
        self.coord = []
        self.coor_X = self.df_filter["Easting"]
        self.coor_Y = self.df_filter["Northing"]
        self.BU_weath_files = []
        self.organizer_f = True  # write (True) or not the organizer file into "hard disk"? Should write just once
        
        
        
    #generate the soil file
    def gen_soils(self):
        # create dictionaries, for point and layers
        # dictinoary and list
        self.BU_site_names = []
        self.point_ID_log = []
        self.coord=[]
        
        count_ini, count_end = int(0), int(0)
        
        # points in a field loop
        for i in range(len(self.val_uniq)):
            count_ini += count_end
            count_end = int( (self.point_ID == self.val_uniq[i]).sum() )
            
            lis_lay=[]
            self.point_ID_log.append(self.point_ID.iloc[count_ini])
            self.coord.append((self.coor_X.iloc[count_ini], self.coor_Y.iloc[count_ini]))
            
            # layers in a point loop
            for ii in range(count_ini, count_ini+count_end, int(1)):
                th_  = round(float(self.lay_thic.iloc[ii]) , 6)
                soc_ = round(float(self.soc.iloc[ii]) , 6)
                k5_  = self.tex.iloc[ii]
                sand_ = round(float(self.sand.iloc[ii]) , 3)
                clay_ = round(float(self.clay.iloc[ii]) , 3)
                sd_  = round(float(self.BD.iloc[ii]) , 6)
                
                dc_  = {
                    "Thickness": [th_, "m"],
                    "SoilOrganicCarbon": [soc_, "%"],
                    "KA5TextureClass": k5_,
                    "Sand": sand_,
                    "Clay": clay_,
                    "SoilBulkDensity": [sd_, "kg m-3"]}
                lis_lay.append(dc_)
            
            # load Json
            js_file = self.soil_template
            
            
            # Alter json file
            js_file["SiteParameters"]["SoilProfileParameters"] = lis_lay
            json_string = json.dumps(js_file, indent=2)
            
            self.BU_site_names.append(f"site_{i}.json")
            with open(os.path.join(self.path_all_out, f"site_{i}.json"), "w") as f:
                f.write(json_string)
        return None
    
    
    # TODO - gernerate weather files
    def gen_weather_init(self):
        self.BU_weath_files = []
        
        # verify weathers folder TODO
        main_weather = os.path.join(self.path_soil_data , self.weather)
        
        
        for i in range(len(self.val_uniq)):
            os.makedirs(os.path.join(self.path_all_out,"weathers") , exist_ok=True)
            t_ = os.path.join(self.path_all_out,"weathers",f"weather_{i}.csv")
            shutil.copy2(main_weather, t_)
            
            self.BU_weath_files.append(t_)
        return None
    
    
    # TODO - put weather files in sim files
    # generate sim file and organizer file
    def gen_sim(self):
        self.BU_out_files = []
        self.BU_sim_files = []
        
        self.BU_weath_files = [path.replace("\\", "/") for path in self.BU_weath_files]
        
        if self.BU_weath_files == []:
            print("all weathers are considered the same")
            for i in range(len(self.val_uniq)):
                self.BU_weath_files.append(self.weather)
        
        # points in a field loop
        for i in range(len(self.val_uniq)):
            
            # load Json
            js_file_ = self.sim_template
            
            # Alter json file
            js_file_["site.json"] = self.BU_site_names[i]
            
            js_file_["output"]["file-name"] = f"out_{i}.csv" # output file
            
            js_file_["climate.csv"] = self.BU_weath_files[i] # TODO - verif!!!
            
            js_file_["climate.csv-options"]["start-date"] = self.start_date
            js_file_["climate.csv-options"]["end-date"] = self.end_date
            
            
            
            json_string = json.dumps(js_file_, indent=2)
            
            # write the Soil file
            with open(os.path.join(self.path_all_out, f"sim_{i}.json"), "w+") as f:
                f.write(json_string)
            
            # append out files in meta organizer
            if self.organizer_f:
                self.BU_out_files.append([f"out_{i}.csv", i])
                self.BU_sim_files.append(f"sim_{i}.json")
        
        # meta file creation, shoukd run just once, if working
        if self.organizer_f:
            try:
                org_ = ["X,Y,field_point_ID_TRUE,simulations_ID,sim_file,site_file,weather_file,out_file\n"]
                for ii in range(len(self.BU_site_names)):
                    v1_1= self.coord[ii][0]
                    v1_2= self.coord[ii][1]
                    v2  = self.point_ID_log[ii]
                    v3  = self.BU_out_files[ii][1]
                    v4  = self.BU_sim_files[ii]
                    v5  = self.BU_site_names[ii]
                    v6  = self.BU_weath_files[ii]
                    v7  = self.BU_out_files[ii][0]
                    t_  = f"{v1_1},{v1_2},{v2},{v3},{v4},{v5},{v6},{v7}\n"
                    org_.append(t_)
                org_res = "".join(org_)
                with open(os.path.join(self.path_all_out, "_meta_organizer.csv"), "w") as f:
                    f.write(org_res)
                self.organizer_f = False
            except Exception as e:
                print(type(e))
                print(str(e))
        return None



# Test
if __name__ == "__main__":
    
    # Path to the folder containing all the raw data
    path_soil_weather_data = r"D:\_Trabalho\_Publicacoes_nossas\Inv_Mod_SHP\__MONICA_New\_Boo_Monica\input_files\raw_data" + os.sep
    
    # Template "sim" and "site" files
    template_sim  = r"sim_template.json"
    template_soil = r"site_template.json"
    
    # soil data, please, use the template
    file_soil = "soil_Boo_lean_share.csv"
    dens = "middle"
    field = "1211"
    weather_file = "109_120_boo-2019-21.csv"
    csv_separator = ","
    path_all_out = r"D:\_Trabalho\_Publicacoes_nossas\Inv_Mod_SHP\__MONICA_New\_Boo_Monica\input_files" + os.sep
    
    start_date = "2020-01-30"
    end_date   = "2021-08-24"
    
    soil_files = write_files(path_soil_weather_data, file_soil, field, dens, path_all_out, weather_file, start_date, end_date, template_sim, template_soil)
    soil_files.gen_soils()
    soil_files.gen_weather_init()
    soil_files.gen_sim()




