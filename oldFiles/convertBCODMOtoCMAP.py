#!/usr/bin/env python
# coding: utf-8

# # convertBCODMOtoCMAP
# Krista Longnecker, 2 July 2025\
# Run this after running getBCODMOinfo.ipynb\
# Once you have the information from BCO-DMO dataset in hand, use this to make it into the format required by CMAP.
# Make this a script so I can just call it from the jupyter notebook.

#some of these are residual from assembling the data file, keep for now.
import pandas as pd
import requests
import os
import json

from datetime import datetime, timedelta, timezone
from SPARQLWrapper import SPARQLWrapper, POST, JSON
from frictionless import describe, Package


# In[2]:


# Make a function that searches for bcodmo:name and returns bcodmo:description and bcodmo:units
# input: md --> the list of parameters for one dataset
def getDetails(md,bcodmo_name):
    """
    Take the list of information from BCO-DMO, search for a name, and return the description and units for that name
    """
    for i, item in enumerate(md):
        if item['bcodmo:name'] == bcodmo_name:
            #actually want the descrption, so return that
            description = item['bcodmo:description']
            units = item['bcodmo:units']

    return description, units


# In[3]:


#read in the package that was already made (using getBCODMOinfo.ipynb)
biosscope = Package('datapackage.json')


# These next cells are left here so I remember ways to access information in the json file, they are just tests

# In[4]:


# #various commands I have been trying to see what is biosscope
# biosscope.get_resource
# biosscope.resources


# In[5]:


#checking out ways to access the information in biosscope
for idx,item in enumerate(biosscope.resources):
    justFile = item.sources[0]['doi']; #apparently I need to index this
    print(justFile)


# In[6]:


out = [];
for idx,item in enumerate(biosscope.resources):
    justFile = item.name;
    #pdb.set_trace()
    out.append(justFile)

out #this will be a list


# In[7]:


for idx,item in enumerate(biosscope.resources):
    justFile = item.path;
    print(justFile)


# # Start working with a data file

# In[ ]:





# In[8]:


#start with the data from the discrete samples (later will go through all the BIOS-SCOPE data files)
workOne = 'survey_biogeochemical'
index = out.index(workOne) #use this for one data set...will later put this into a loop
print(f"Found the discrete data at index {index}") # Output: Found at index #
#use that to find the right filename
#biosscope.resources[index]


# In[ ]:





# In[20]:


data_url = biosscope.resources[index].path


# In[ ]:


if data_url.endswith('csv'):
    #for BIOS-SCOPE there are datafiles that are tar.gz files with actual images, don't need those 
    #so (for now at least) I will filter to see if the datafile is a CSV file. Sort out if there is 
    #a better way to deal with that distinction.
    
    #super easy to work with the CSV file once I have the URL
    bcodmo = pd.read_csv(data_url,na_values = ['nd']) #now I have NaN...but they get dropped when writing the file


# In[10]:


#start with the first sheet, data, and setup the data into the CMAP format, generating a multi-page Excel file

# Required variables are time, lat, lon, depth
df = pd.DataFrame(columns=['time','lat','lon','depth'])

# time --> CMAP requirement is this: #< Format  %Y-%m-%dT%H:%M:%S,  Time-Zone:  UTC,  example: 2014-02-28T14:25:55 >
# Do this in two steps so I can check the output more easily
temp = bcodmo.copy()
temp['date'] = pd.to_datetime(temp['decy'], unit='D', origin='1970-01-01')
temp['date_cmap'] = temp['date'].dt.strftime("%Y-%m-%dT%H:%M:%S")
df['time'] = temp['date_cmap']

# lat (-90 to 90) and lon (-180 to 180); use variable names at BCO-DMO
df['lat'] = bcodmo['Latitude']
df['lon'] = bcodmo['Longitude']  #BCO-DMO already has this as negative
df['depth'] = bcodmo['Depth']

# all remaining columns in bcodmo can be considered data
#remember: bcodmo_trim will have the list of variables that I will use later to get metadata about the variables
bcodmo_trim = bcodmo.drop(columns=['Latitude', 'Longitude', 'Depth'])
nVariables = bcodmo_trim.shape[1] #remember in Python indexing starts with 0 (rows, 1 is the columns)
# and then add to the datafile I am assembling (essentially re-order columns
df = pd.concat([df, bcodmo_trim], axis=1)


# In[11]:


# work on the second sheet: metadata about the variables; use the CMAP dataset template to setup the dataframe so I get the column headers right
fName = 'datasetTemplate.xlsx'
sheet_name = 'vars_meta_data'
vars = pd.read_excel(fName, sheet_name=sheet_name)
cols = vars.columns.tolist()
#df2 will be the dataframe with the metadata about the variables, set it up empty here
df2 = pd.DataFrame(columns=cols,index = pd.RangeIndex(start=0,stop=nVariables)) #remember, Python is 0 indexed

#the variables I need to search for are here: bcodmo_trim.columns, put them in the first column
df2['var_short_name'] = bcodmo_trim.columns
#Need the information from BCO-DMO to fill in the metadata about the variables.
md = biosscope.resources[6].custom['bcodmo:parameters'] #this is a list, don't forget 'custom' (!!) that is not obvious when you look at the json file


# In[12]:


#there is most certainly a better way to do this, but I understand this option
for idx,item in enumerate(df2.iterrows()):
    a,b = getDetails(md,df2.loc[idx,'var_short_name']) #getDetails is the function I wrote (see above)
    df2.loc[idx,'var_long_name'] = a
    df2.loc[idx,'var_unit'] = b


# In[13]:


#for sensor I will need a lookup table as the information at BCO-DMO is not formatted to provide this. There is some
#sensor information, but I don't see how it is linked directly to specific measured variables, and more than one variable can match a given sensor.
#Later note, probably easier to put this into Excel (see notes below about the CMAP keywords that are required)


#13 options listed at BCO-DMO:manually assign to one or more variables as possible
LUsensors = {'CTD SeaBird 911+':['Temp','CTD_SBE35T','Conductivity','Pressure'],
             'Lachat QuikChem 8500 series 2':['NO3_plus_NO2','NO3','NO2','PO4','NH4','SiO2'],
             'Shimadzu TOC-V':['DOC'],
             'TNM-1 chemiluminescent detector assembly':['TDN'],
             'Olympus BX51 epifluorescent microscope':['Bact']
            }

# These other sensors are for data I have not yet tackled, leave here for now
# 'MOCNESS'
# 'Reeve net'

# 'CEC 440HA combustion analyzer'

# ##glider, not yet ready, so hold off one these
# 'Slocum G2 glbider'
# 'WetLabs ECOpuck (ChlF and Bp700)'
# 'Submersible Underwater Nitrate Analyzer (SUNA)'
# 'Aanderaa O2 optode'


# In[14]:


# this will return the sensor given a possible variable, surely there is a better way to do this...
for idx,item in enumerate(df2.iterrows()):
    oneVar = df2.loc[idx,'var_short_name']
    sensor =  str([k for k, v in LUsensors.items() if oneVar in v])[2:-2]
    if len(sensor): #only try and fill in if a sensor was found
        df2.loc[idx,'var_sensor'] = str(sensor) #strip off the [] at the beginning/end of the list


# In[15]:


#there are a few pieces of metadata that CMAP wants that will be easier to track in an Excel file -
#make the file once, and then update as needed for future BCO-DMO datasets.
#The keywords include cruises, and all possible names for a variable. I wonder if
#CMAP has that information available in a way that can be searched?
# Note that I made the Excel file after I started down this rabbit hole with the sensors. It will probably make sense
#to pull the sensor information from the file as well.
fName = 'CMAP_variableMetadata_additions.xlsx'
moreMD = pd.read_excel(fName,sheet_name = 'vars_meta_data')


# In[16]:


#suffixes are added to column name to keep them separate; '' adds nothing while '_td' adds _td that can get deleted next
df2 = moreMD.merge(df2[['var_short_name','var_keywords']],on='var_short_name',how='right',suffixes=('', '_td',))
# Discard the columns that acquired a suffix:
df2 = df2[[c for c in df2.columns if not c.endswith('_td')]]

#these two are easy: just add them here
df2.loc[:,('var_spatial_res')] = 'irregular'
df2.loc[:, ('var_temporal_res')] = 'irregular'


# In[17]:


#metadata about the project

# finally gather up the dataset_meta_data: for now I just wrote the information here, I might setup in a separate text file later
df3 = pd.DataFrame({
    'dataset_short_name': ['BIOSSCOPE_v1'],
    'dataset_long_name': ['BIOS-SCOPE ' + workOne],
    'dataset_version': ['1.0'],
    'dataset_release_date': ['2025-06-25'],
    'dataset_make': ['observation'],
    'dataset_source': ['Craig Carlson, Bermuda Institute of Ocean Sciences'],
    'dataset_distributor': ['Craig Carlson, Bermuda Institute of Ocean Sciences'],
    'dataset_acknowledgement': ['We thank the BIOS-SCOPE project team and the BATS team for assistance with sample collection, processing, and analysis. The efforts of the captains, crew, and marine technicians of the R/V Atlantic Explorer are a key aspect of the success of this project. This work supported by funding from the Simons Foundation International.'],
    'dataset_history': [''],
    'dataset_description': ['This dataset includes analyses from Niskin bottle samples collected on R/V Atlantic Explorer cruises as part of the BIOS-SCOPE campaign in the time period from 2016 until 2025. Included are CTD data, and survey biogeochemical samples including inorganic nutrients, particulate organic carbon and nitrogen, dissolved organic carbon, dissolved organic nitrogen, total dissolved amino acids, bacterial abundance and production.'],
    'dataset_references': ['Carlson, C. A., Giovannoni, S., Liu, S., Halewood, E. (2025) BIOS-SCOPE survey biogeochemical data as collected on Atlantic Explorer cruises (AE1614, AE1712, AE1819, AE1916) from 2016 through 2019. Biological and Chemical Oceanography Data Management Office (BCO-DMO). (Version 1) Version Date 2021-10-17. doi:10.26008/1912/bco-dmo.861266.1 [25 June 2025]'],
    'climatology': [0]
    })

#get the list of cruise names from the bcodmo data file
t = pd.DataFrame(bcodmo['Cruise_ID'].unique())
t.columns = ['cruise_names']
df3 = pd.concat([df3,t],axis=1,ignore_index = True)


# In[18]:


#export the result as an Excel file with three tabs
#make the data folder if it is not already there (it is in .gitignore, so it will not end up at GitHub)
folder = "data"
os.chdir(".")

if os.path.isdir(folder):
    print("Data will go here: %s" % (os.getcwd()) + '\\' + folder)
else:
    os.mkdir(folder)

fName_CMAP = 'data/forCMAPfromBCODMOwithPython.xlsx'
dataset_names = {'data': df, 'dataset_meta_data': df3, 'vars_meta_data': df2}
with pd.ExcelWriter(fName_CMAP) as writer:
    for sheet_name, data in dataset_names.items():
        data.to_excel(writer, sheet_name=sheet_name, index=False)


# In[ ]:





# In[ ]:





# In[ ]:





# In[19]:


raise UserWarning('Stopping and leave code below for historical reasons, code will not run')


# In[ ]:


## Keep this next cell to share feedback
#Need the information from BCO-DMO to fill in the metadata about the variables.
## took me a while to figure out that I needed 'custom' to access the BCO-DMO parameters. It shows up in the original
# code Adam wrote to gather the information, but when you look at biosscope.resources[6] the information is not listed
# under 'custom', so that required some digging around
# The following syntaxes do not work, and I tried them all before I figured out  I need 'custom'
# md = biosscope.resources[6].['bcodmo:parameters']
# md = biosscope.resources[6].{['bcodmo:parameters']}
# md = biosscope.resources[6].[{'bcodmo:parameters'}]
# md = biosscope.resources[6].'bcodmo:parameters'

## THIS WORKS
# md = biosscope.resources[6].custom['bcodmo:parameters'] #this is a list


# In[ ]:


#use this for debugging
import pdb
#put this where I need to stop #pdb.set_trace()


# In[ ]:


get_ipython().run_line_magic('reset', '-f')

