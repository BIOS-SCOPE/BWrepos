# BWrepos
Scripting access to transfer data from one repository to another\
Krista Longnecker

Most recent comments at the top.
### 14 August 2025
Make repository public.

### 18 July 2025
Set up three scripts that actually convert the BCO-DMO data into the CMAP format, one script for each group (Carlson, Close, Blanco-Bercial/Maas). Those scripts are called by a Jupyter notebook, with the end result of the Excel files (one Excel file per dataset). 
- [ ] get permissions to submit these to CMAP

### 16 July 2025
The added metadata for the variables is a series of one-offs. It might make sense to manually add the details as each file is different.

### 15 July 2025
Working on the pump data (with 'Depth' and 'Depth_m' appearing as variables...dealt with that), using a second script (```convert_pumpData.py```). \
- [x] need to sort out metadata about variables (right now it only works for the discrete file)
- [x] the zoop data will require parsing out names and merging the sample rows with the separate metadata file

### 13 July 2025
Change to using ```convert.py``` to a script, but now I realize that even within BIOS-SCOPE the differnt data files all have super different formats so this is not going to be easily scripted. Right now this works for the discrete data file, but the zooplankton group has a different format and presumably the particle data will also be different.

### 5 July 2025
All set with the biogeochemical data - I can go from BCO-DMO to CMAP in one Python notebook. Move this repository over the BIOS-SCOPE, but still keep it private. 
To get this to work, first run ```getBCODMOinfo.ipynb``` and then run ```convertBCODMOtoCMAP.ipynb``` and the end results is an Excel file with the three required worksheets.

### 3 July 2025
I can now use the data in the frictionless/json file and put it into the CMAP format. Next step will be to get the metadata about the different variables.

### 29 June 2025
Adam Shepard set up the script I need to access the data in BCO-DMO and the end result is a Frictionless data package. 

- [x] Convert the information in the Frictionless package to the CMAP format
- [x] Check out Adam's code
 
### 27 June 2025
Keep this private for now as I am starting with code that is not yet publically available.

