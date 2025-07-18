# Krista Longnecker, 13 July 2025
# Run this after running getBCODMOinfo.ipynb
# This script will convert the BCO-DMO json file into the format required by CMAP
# this script works on the zooplankton data from BIOS, Leocadio Blanco-Bercial and Amy Maas

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
            #for the zoop data have bcodmo parts with no units
            if 'bcodmo:units' in item:
                units = item['bcodmo:units']
            else:
                units = 'not applicable'

    return description, units


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
    #pdb.set_trace()
    temp['date'] = pd.to_datetime(temp['ISO_DateTime_UTC'])
    temp['date_cmap'] = temp['date'].dt.strftime("%Y-%m-%dT%H:%M:%S")
    df['time'] = temp['date_cmap']
    
    # lat (-90 to 90) and lon (-180 to 180); use variable names at BCO-DMO
    df['lat'] = bcodmo['object_lat']
    df['lon'] = bcodmo['object_lon']  #BCO-DMO already has this as negative

    #depth in the zooplankton data are a range from min to max, select a number in the middle
    df['depth'] = bcodmo['object_depth_max'] - bcodmo['object_depth_min']

    #the object_id has the cruise information that will be needed later...pull that out of object_id
    temp['Cruise'] = ''
    for i,item in temp.iterrows():
        c = re.split('_',temp.loc[i,'object_id'])
        oneC = [c[n] for n in (0,)]
        #pdb.set_trace()
        temp.loc[i,'Cruise'] = oneC[-1]
    
    # all remaining columns in bcodmo can be considered data
    #for the zoop data - keep min and max depth
    bcodmo_trim = bcodmo.drop(columns=['object_lat', 'object_lon'])
    nVariables = bcodmo_trim.shape[1] #remember in Python indexing starts with 0 (rows, 1 is the columns)
    # and then add to the datafile I am assembling (essentially re-order columns
    df = pd.concat([df, bcodmo_trim], axis=1)
       
    # work on the second sheet: metadata about the variables; use the CMAP dataset template to setup the dataframe so I get the column headers right
    templateName = 'datasetTemplate.xlsx'
    sheet_name = 'vars_meta_data'
    vars = pd.read_excel(templateName, sheet_name=sheet_name)
    cols = vars.columns.tolist()
    #df2 will be the dataframe with the metadata about the variables, set it up empty here
    df2 = pd.DataFrame(columns=cols,index = pd.RangeIndex(start=0,stop=nVariables)) #remember, Python is 0 indexed
    
    #the variables I need to search for are here: bcodmo_trim.columns, put them in the first column
    df2['var_short_name'] = bcodmo_trim.columns
        
    #there is most certainly a better way to do this, but I understand this option
    for idx,item in enumerate(df2.iterrows()):
        #somehow one variable at BCO-DMO does not have a bcodmo:unit option (it's unitless, but still)
        if df2.loc[idx,'var_short_name'] != 'object_id':
            a,b = getDetails(md,df2.loc[idx,'var_short_name']) #getDetails is the function I wrote (see above)
            df2.loc[idx,'var_long_name'] = a
            df2.loc[idx,'var_unit'] = b
        elif df2.loc[idx,'var_short_name'] == 'object_id':
            df2.loc[idx,'var_long_name'] = 'Particle identifier'
            df2.loc[idx,'var_unit'] = 'unitless'
      
    # These other sensors are for data I have not yet tackled, leave here for now
    # 'MOCNESS'
    # 'Reeve net'
    
    #there are a few pieces of metadata that CMAP wants that will be easier to track in an Excel file -
    #make the file once, and then update as needed for future BCO-DMO datasets.
    #The keywords include cruises, and all possible names for a variable.
    # There are so many CMAP specific options that it is easier to run this 2x and add the custom pieces to a new sheet in the Excel file
    fName = 'CMAP_variableMetadata_additions.xlsx'
    sheetName = exportFile[0:31] #Excel limits the length of the sheet name
    moreMD = pd.read_excel(fName,sheet_name = sheetName)
   
    #suffixes are added to column name to keep them separate; '' adds nothing while '_td' adds _td that can get deleted next
    df2 = moreMD.merge(df2[['var_short_name','var_keywords']],on='var_short_name',how='right',suffixes=('', '_td',))
    # Discard the columns that acquired a suffix:
    df2 = df2[[c for c in df2.columns if not c.endswith('_td')]]
    
    #these two are easy: just add them here
    df2.loc[:,('var_spatial_res')] = 'irregular'
    df2.loc[:, ('var_temporal_res')] = 'irregular'

    # finally gather up the dataset_meta_data: into a third data frame (df3)
    df3 = pd.DataFrame({
        'dataset_short_name': ['BIOSSCOPE_v1'],
        'dataset_long_name': ['BIOS-SCOPE_' + exportFile],
        'dataset_version': ['1.0'],
        'dataset_release_date': [date.today()],
        'dataset_make': ['observation'],
        'dataset_source': ['Leocadio Blanco-Bercial (Bermuda Institute of Ocean Sciences)'],
        'dataset_distributor': ['Leocadio Blanco-Bercial (Bermuda Institute of Ocean Sciences)'],
        'dataset_acknowledgement': ['We thank the BIOS-SCOPE project team and the BATS team for assistance with sample collection, processing, and analysis. The efforts of the captains, crew, and marine technicians of the R/V Atlantic Explorer are a key aspect of the success of this project. This work supported by funding from the Simons Foundation International.'],
        'dataset_history': [''],
        'dataset_description': [biosscope.resources[idx_json].sources[0]['title']],
        'dataset_references': ['Maas, A. E., Gossner, H., Smith, M. J., & Blanco-Bercial, L. (2021). Use of optical imaging datasets to assess biogeochemical contributions of the mesozooplankton. Journal of Plankton Research, 43(3), 475–491. doi:10.1093/plankt/fbab037'],
        'climatology': [0]
        })
    
    #get the list of cruise names from the bcodmo data file
    t = pd.DataFrame(temp['Cruise'].unique()) #I put the cruise-only information in temp
    t.columns = ['cruise_names']
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
