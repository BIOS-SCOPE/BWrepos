# Krista Longnecker, 13 July 2025
# Updating 17 August 2025 to fine tune this script
# Run this after running getBCODMOinfo.ipynb
# This script will convert the BCO-DMO json file into the format required by CMAP
# Work on the input for one file, with the end result as one Excel file; will only end up here if the data 
# file is a CSV file
# This script works on the discrete data file (the first one I wrote)


#some of these are residual from assembling the data file, keep for now.
import pandas as pd
import requests
import os
import json
import re
import sys
import pdb
from datetime import date
from frictionless import describe, Package

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

#set up a function to remove <p> and </p> from the beginning and end, occurs multiple times
def clean(a):
    """Some of the descriptions have added markers, remove them using this function"""
    if a.startswith('<p>'):
        toStrip = '[</p><p>]'
        clean = re.sub(toStrip,'',a)
    elif a.endswith('.'):
        clean = re.sub('\.$','',a)
    else:
        clean = a
    
    return clean


def main():
    '''
    Go through the steps needed to go from BCO-DMO details in json file and end with output that is an Excel file
    '''
    idx_json = int(sys.argv[1])
    #to do: figure out a better way to do this so I am not reading in the json file every time
    biosscope = Package('datapackage.json')
    
    data_url = biosscope.resources[idx_json].path
    md = biosscope.resources[idx_json].custom['bcodmo:parameters'] #this is a list, don't forget 'custom' (!!)

    #make a short name out of the data_url, will use this as part of the name for the final Excel file 
    exportFile = re.split('/',data_url).pop().replace('.csv','')

    #super easy to work with the CSV file once I have the URL
    bcodmo = pd.read_csv(data_url,na_values = ['nd']) #now I have NaN...but they get dropped when writing the file
        
    # Required variables are time, lat, lon, depth
    df = pd.DataFrame(columns=['time','lat','lon','depth'])
    
    # time --> CMAP requirement is this: #< Format  %Y-%m-%dT%H:%M:%S,  Time-Zone:  UTC,  example: 2014-02-28T14:25:55 >
    # Do this in two steps so I can check the output more easily
    temp = bcodmo.copy()
    #you have to change this to a string (.apply(str)) or else this cannot get converted to an Excel variable.
    #pdb.set_trace()
    temp['date'] = pd.to_datetime(temp['ISO_DateTime_UTC'])
    temp['date_cmap'] = temp['date'].dt.strftime("%Y-%m-%dT%H:%M:%S" + "+00:00")
    
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
       
    # work on the second sheet: metadata about the variables; use the CMAP dataset template to setup the dataframe so I get the column headers right
    templateName = 'datasetTemplate.xlsx'
    sheet_name = 'vars_meta_data'
    vars = pd.read_excel(templateName, sheet_name=sheet_name)
    metaVarColumns = vars.columns.tolist()
    #cols = vars.columns.tolist()
    #df2 will be the dataframe with the metadata about the variables, set it up empty here
    df2 = pd.DataFrame(columns=metaVarColumns,index = pd.RangeIndex(start=0,stop=nVariables)) #remember, Python is 0 indexed
    
    #the variables I need to search for are here: bcodmo_trim.columns, put them in the first column
    df2['var_short_name'] = bcodmo_trim.columns
        
    #there is most certainly a better way to do this, but I understand this option
    for idx,item in enumerate(df2.iterrows()):
        a,b = getDetails(md,df2.loc[idx,'var_short_name']) #getDetails is the function I wrote (see above)
        # var_unit has to be 50 characters or less...for now this only happens 1x, so manually edit
        #pdb.set_trace()
#         if b == 'microEinsteins per second per square meter (uE/m^2/sec)':
#             #pdb.set_trace()
#             b = 'microEinsteins per square meter per sec(μE/m2-sec)'
#         elif b == 'cells times 100 million per kilogram (cells*10^8/kg)':
#             b = 'cells times 100 million per kilogram'
#         elif a == 'Temperature from SeaBird 35 CTD which has 8 second average taken at time of the bottle fire. This sensor has an accuracy of 0.0001C as compared to the standard profiling units which have an accuracy of 0.002C.':
#             a = 'Temperature from SeaBird 35 CTD which has 8 second average taken at time of the bottle fire'
        
        #pdb.set_trace()
        
        df2.loc[idx,'var_long_name'] = clean(a)
        df2.loc[idx,'var_unit'] = b
        
    #these two are easy: just add them here
    df2.loc[:,('var_spatial_res')] = 'irregular'
    df2.loc[:, ('var_temporal_res')] = 'irregular'
       
    #there are a few pieces of metadata that CMAP wants that will be easier to track in an Excel file -
    #make the file once, and then update as needed for future BCO-DMO datasets.
    #The keywords include cruises, and all possible names for a variable. I wonder if
    #CMAP has that information available in a way that can be searched?
    # Note that I made the Excel file after I started down this rabbit hole with the sensors. It will probably make sense
    #to pull the sensor information from the file as well.
    fName = 'CMAP_variableMetadata_additions.xlsx'
    sheetName = exportFile[0:31] #Excel limits the length of the sheet name
    moreMD = pd.read_excel(fName,sheet_name = sheetName)
   
    #suffixes are added to column name to keep them separate; '' adds nothing while '_td' adds _td that can get deleted next
    df2 = moreMD.merge(df2[['var_short_name','var_keywords']],on='var_short_name',how='right',suffixes=('', '_td',))
    # Discard the columns that acquired a suffix:
    df2 = df2[[c for c in df2.columns if not c.endswith('_td')]]
    

    #if moreMD is empty add the details to the CMAP_variableMetdata_additions.xlsx file so I can fill in the information
    if len(moreMD)==0:
        with pd.ExcelWriter(fName, engine='openpyxl', mode='a',if_sheet_exists = 'replace') as writer:  
            df2.to_excel(writer, sheet_name=sheetName,index = False)
    else:  
        #otherwise merge the information from moreMD into df2
        #suffixes are added to column name to keep them separate; '' adds nothing while '_td' adds _td that can get deleted next
        #update to remove var_sensor as that is now in the Excel file with the metadata details
        df2 = moreMD.merge(df2[['var_short_name','var_long_name','var_unit']],on='var_short_name',how='left',suffixes=('_td', '',))
        
        # Discard the columns that acquired a suffix:
        df2 = df2[[c for c in df2.columns if not c.endswith('_td')]]
        #reorder the result to match the expected order        
        df2 = df2.loc[:,metaVarColumns]
        
        
    #There are some data columns that are empty because the variables are not included 
    #in what is submitted to BCO-DMO. These need to be removed from the data file before 
    #it is submitted to CMAP
    #NO3, NO3_QF, NO2, NO2_QF, NH4, NH4_QF, SiO2, SiO2_QF, Phe
    #The nutrients are measured by BATS and not submitted here, Phe has a conflicting peak and does not get reported.
    toDelete = {'NO3', 'NO3_QF', 'NO2', 'NO2_QF', 'NH4', 'NH4_QF', 'SiO2', 'SiO2_QF', 'Phe'}
    df.drop(columns = toDelete,inplace = True)

    #also need to drop these rows from the metadata about the variables
    #pdb.set_trace()
    indices_to_drop = df2[df2['var_short_name'].isin(toDelete)].index
    df2.drop(indices_to_drop, inplace=True)
       
    #metadata about the project    
    # finally gather up the dataset_meta_data: for now I just wrote the information here, I might setup in a separate text file later
    #pdb.set_trace()
    df3 = pd.DataFrame({
        'dataset_short_name': ['BIOSSCOPE_' + exportFile],
        'dataset_long_name': ['BIOS-SCOPE ' + exportFile],
        'dataset_version': ['1.0'],
        'dataset_release_date': [date.today()],
        'dataset_make': ['observation'],
        'dataset_source': ['Craig Carlson, Bermuda Institute of Ocean Sciences'],
        'dataset_distributor': ['Craig Carlson, Bermuda Institute of Ocean Sciences'],
        'dataset_acknowledgement': ['We thank the BIOS-SCOPE project team and the BATS team for assistance with sample collection, processing, and analysis. The efforts of the captains, crew, and marine technicians of the R/V Atlantic Explorer are a key aspect of the success of this project. This work supported by funding from the Simons Foundation International.'],
        'dataset_history': [''],
        'dataset_description': [biosscope.resources[idx_json].sources[0]['title']],
        'dataset_references': ['Carlson, C. A., Giovannoni, S., Liu, S., Halewood, E. (2025) BIOS-SCOPE survey biogeochemical data as collected on Atlantic Explorer cruises (AE1614, AE1712, AE1819, AE1916) from 2016 through 2019. Biological and Chemical Oceanography Data Management Office (BCO-DMO). (Version 1) Version Date 2021-10-17. doi:10.26008/1912/bco-dmo.861266.1 [25 June 2025]'],
        'climatology': [0]
        })
    
    #get the list of cruise names from the bcodmo data file
    t = pd.DataFrame(bcodmo['Cruise_ID'].unique())
    t.columns = ['cruise_names']
    #df3 = pd.concat([df3,t],axis=1,ignore_index = True)
    df3 = pd.concat([df3,t],axis=1)

    #export the result as an Excel file with three tabs
    #make the data folder if it is not already there (it is in .gitignore, so it will not end up at GitHub)
    folder = "data"
    os.chdir(".")
    
    if os.path.isdir(folder):
        print("Data will go here: %s" % (os.getcwd()) + '\\' + folder + '\\' + exportFile)
    else:
        os.mkdir(folder)
    
    fName_CMAP = 'data/' + 'BIOSSCOPE_' + exportFile + '.xlsx' 
    dataset_names = {'data': df, 'dataset_meta_data': df3, 'vars_meta_data': df2}
    with pd.ExcelWriter(fName_CMAP) as writer:
        for sheet_name, data in dataset_names.items():
            data.to_excel(writer, sheet_name=sheet_name, index=False)




#######################################
#                                     #
#                                     #
#                 main                #
#                                     #
#                                     #
#######################################

if __name__ == "__main__":    
    main()    
