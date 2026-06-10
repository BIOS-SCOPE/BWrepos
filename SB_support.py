#!/usr/bin/env python

""" Module for manipulating data from NASA GSFC SeaBASS files.

Original author: Joel Scott, SAIC / NASA GSFC Ocean Ecology Lab
Contributor: Michael Maniscalco, SSAI/ NASA GSFC Ocean Ecology Lab 20260403

Notes:
* This module is designed to work with files that have been properly
  formatted according to SeaBASS guidelines (i.e. Files that passed FCHECK).
  Some error checking is performed, but improperly formatted input files
  could cause this script to error or behave unexpectedly. Files
  downloaded from the SeaBASS database should already be properly formatted, 
  however, please email seabass@seabass.gsfc.nasa.gov and/or the contact listed
  in the metadata header if you identify problems with specific files.

* It is always HIGHLY recommended that you check for and read any metadata
  header comments and/or documentation accompanying data files. Information 
  from those sources could impact your analysis.

* Compatibility: This module was developed for Python 3.6, using Python 3.6.3

/*=====================================================================*/
                 NASA Goddard Space Flight Center (GSFC) 
         Software distribution policy for Public Domain Software

 The readsb code is in the public domain, available without fee for 
 educational, research, non-commercial and commercial purposes. Users may 
 distribute this code to third parties provided that this statement appears
 on all copies and that no charge is made for such copies.

 NASA GSFC MAKES NO REPRESENTATION ABOUT THE SUITABILITY OF THE SOFTWARE
 FOR ANY PURPOSE. IT IS PROVIDED "AS IS" WITHOUT EXPRESS OR IMPLIED
 WARRANTY. NEITHER NASA GSFC NOR THE U.S. GOVERNMENT SHALL BE LIABLE FOR
 ANY DAMAGE SUFFERED BY THE USER OF THIS SOFTWARE.
/*=====================================================================*/

"""
import re
from collections import OrderedDict
from datetime import datetime

#==========================================================================================================================================

class readSB:
    """ Read an FCHECK-verified SeaBASS formatted data file.
        Required arguments:
        filename = name of SeaBASS input file (string)

        Optional arguments:
        mask_missing               = flag to set missing values to NaN, default set to True
        mask_above_detection_limit = flag to set above_detection_limit values to NaN, default set to True
        mask_below_detection_limit = flag to set below_detection_limit values to NaN, default set to True
        no_warn                    = flag to suppress warnings, default set to False
        
        Returned data structures:
        .filename  = name of data file
        .headers   = dictionary of header entry and value, keyed by header entry
        .comments  = list of strings containing the comment lines from the header information
        .missing   = fill value as a float used for missing data, read from header
        .variables = dictionary of field name and unit, keyed by field name
        .data      = dictionary of data values, keyed by field name, returned as a list
        .length    = number of rows in the data matrix (i.e. the length of each list in data)
        .bdl       = fill value as a float used for below detection limit, read from header (empty if missing or N/A)
        .adl       = fill value as a float used for above detection limit, read from header (empty if missing or N/A)

        Returned sub-functions:
        .fd_datetime()                                  - Converts date and time information from the file's data matrix to a Python
                                                          list of datetime objects
        .addDataToOutput(irow,var_name,units,var_value) - Adds or appends single data point to data matrix given row index, field name,
                                                          field units, and data value, handling fields & units headers and missing values
        .writeSBfile(ofile)                             - Writes headers, comments, and data into a SeaBASS file specified by ofile
        .isnumber(s)                                    - Determines if a given string is a number or not, does not handle complex numbers
                                                          returns True for int, float, or long numbers, else False
                                                          syntax: is_number(str)
        .is_int(s)                                      - Determines if a given string is an integer or not, uses int()
                                                          returns True for int numbers, else False
                                                          syntax: is_int(str)
        .doy2mndy(yr, doy)                              - Returns the month and day of month as integers
                                                          given year and julian day
                                                          syntax: [mn, dy] = doy2mndy(yr, doy)
        
    """
    @staticmethod
    def is_number(s):
        try:
            float(s) # handles int, long, and float, but not complex
        except ValueError:
            return False
        return True
    #=========================================
    @staticmethod
    def is_int(s):
        try:
            int(s) # handles int
        except ValueError:
            return False
        return True
    #=========================================
    @staticmethod
    def doy2mndy(yr, doy):
        dt = datetime.strptime(f'{yr:04d}{doy:03d}', '%Y%j')  # noqa: DTZ007
        return int(dt.strftime('%m')),int(dt.strftime('%d'))
    
    def __init__(self, 
                 filename, 
                 mask_missing=True, 
                 mask_above_detection_limit=True, 
                 mask_below_detection_limit=True, 
                 no_warn=False, 
                 mask_commented_headers = True):

        self.filename          = filename
        self.headers           = OrderedDict()
        self.comments          = []
        self.variables         = OrderedDict()
        self.data              = OrderedDict()
        self.missing           = ''
        self.adl               = ''
        self.bdl               = ''
        self.pi                = ''
        self.length            = 0
        self.empty_col         = []
        self.data_use_warning  = False
        self.err_suffixes      = ['_cv', '_sd', '_se', '_unc','_bincount']

        end_header             = False
        #utility functions put here instead of outside of class because it was making it very hard to import into other classes/packages

        try:
            with open(self.filename, 'r') as fileobj:
                lines = fileobj.readlines()
        except OSError as e:
           raise OSError(f'Unable to open or read file: {self.filename}. Error: {e}')




        """ Remove any/all newline and carriage return characters """
        lines = [re.sub("[\r\n]+",'',line).strip() for line in lines]

        for line in lines:

            """ Extract header """
            if not end_header \
                and not '/begin_header' in line.lower() \
                and not '/end_header' in line.lower() \
                and not '!' in line:
                try:
                    [h,v] = line.split('=', 1)
                    h = h.lower()

                    h = h[1:]
                    self.headers[h] = v
                except ValueError:
                    raise ValueError(f'Unable to parse header key/value pair. Is this a SeaBASS file: {self.filename}\nLine: {line}')

            """ Extract fields """
            if '/fields=' in line.lower() and not '!' in line:
                try:
                    _vars = line.split('=', 1)[1].lower().split(',')
                    for var in _vars:
                        self.data[var] = []
                except (IndexError, ValueError) as e:
                    raise ValueError(f'Unable to parse /fields in file: {self.filename}. Error: {e}. In line: {line}') from e

            """ Extract units """
            if '/units=' in line.lower() and not '!' in line:
                _units = line.split('=', 1)[1].lower().split(',')

            """ Extract missing val """
            if '/missing=' in line.lower() and not '!' in line:
                try:
                    self.missing = float(line.split('=', 1)[1])
                except (IndexError, ValueError) as e:
                    raise ValueError(f'Unable to parse /missing value in file: {self.filename}. Error: {e}. In line: {line}') from e

            """ Extract optical depth warning """
            if '/data_use_warning=' in line.lower() and not '!' in line:
                self.data_use_warning = True

            """ Extract below detection limit """
            if '/below_detection_limit=' in line.lower() and not '!' in line:
                try:
                    self.bdl = float(line.split('=', 1)[1])
                except (IndexError, ValueError) as e:
                    raise ValueError(f'Unable to parse /below_detection_limit value in file: {self.filename}. Error: {e}. In line: {line}') from e

            """ Extract above detection limit """
            if '/above_detection_limit=' in line.lower() and not '!' in line:
                try:
                    self.adl = float(line.split('=', 1)[1])
                except (IndexError, ValueError) as e:
                    raise ValueError(f'Unable to parse /above_detection_limit value in file: {self.filename}. Error: {e}. In line: {line}') from e

            """ Extract PI """
            if '/investigators=' in line.lower() and not '!' in line:
                self.pi = line.split('=', 1)[1].split(',', 1)[0]

            """ Extract delimiter """
            if '/delimiter=' in line.lower() and '!' not in line:
                if 'comma' in line.lower():
                    delim = r',+'
                elif 'space' in line.lower():
                    delim = r'\s+'
                elif 'tab' in line.lower():
                    delim = r'\t+'
                else:
                    raise ValueError(f'Invalid delimiter detected in file: {self.filename}. In line: {line}')

            """ Extract comments, but not history of metadata changes """
            #unless specified
            if mask_commented_headers:
                if '!' in line and '!/' not in line:
                    self.comments.append(line[1:])
            else:
                if '!' in line:
                    self.comments.append(line[1:])

            # Check for required SeaBASS file header elements before parsing data matrix
            if '/end_header' in line.lower():
                if not delim:
                    raise ValueError(f'No valid /delimiter detected in file: {self.filename}')

                if not self.missing:
                    raise ValueError(f'No valid /missing value detected in file: {self.filename}')

                if not _vars:
                    raise ValueError(f'No /fields detected in file: {self.filename}')

                if self.data_use_warning and not no_warn:
                    print(
                        f'Warning: data_use_warning header is present in file: {self.filename}. '
                        'This file contains measurements collected under unique conditions. '
                        'Use with caution and consult headers, file comments, and documentation '
                        'for additional information. Use no_warn=True to suppress this message.'
                    )

                if mask_above_detection_limit and not no_warn and not self.adl:
                    print(
                        f'Warning: No above_detection_limit in file: {self.filename}. '
                        'Unable to mask values as NaNs. Use no_warn=True to suppress this message.'
                    )

                if mask_below_detection_limit and not no_warn and not self.bdl:
                    print(
                        f'Warning: No below_detection_limit in file: {self.filename}. '
                        'Unable to mask values as NaNs. Use no_warn=True to suppress this message.'
                    )

                end_header = True
                continue

            # Extract data after headers
            if end_header and line:
                try:
                    for var, dat in zip(_vars, re.split(delim, line)):
                        if self.is_number(dat):
                            if self.is_int(dat):
                                dat = int(dat)
                            else:
                                dat = float(dat)

                            if mask_above_detection_limit and self.adl != '' and dat == float(self.adl):
                                dat = float('nan')

                            if mask_below_detection_limit and self.bdl != '' and dat == float(self.bdl):
                                dat = float('nan')

                            if mask_missing and dat == self.missing:
                                dat = float('nan')

                        self.data[var].append(dat)

                    self.length += 1

                except (ValueError, TypeError) as e:
                    raise ValueError(f'Unable to parse data from line in file: {self.filename}. Error: {e}. In line: {line}') from e

        try:
            self.variables = OrderedDict(zip(_vars, zip(_vars, _units)))
        except (NameError, TypeError):
            if not no_warn:
                print(
                    f'Warning: No valid units were detected in file: {self.filename}. '
                    'Use no_warn=True to suppress this message.'
                )
            self.variables = OrderedDict(zip(_vars, _vars))

#==========================================================================================================================================
    #fractional seconds can have anywhere from 1 to 6 digits, but datetime will prepend 0s to number until it is 6 digits for some reason
    def millisecondToMicrosecond(self, millisecond):
        while(len(millisecond)< 6):
            millisecond += '0'
        return millisecond
    def fd_datetime(self):
        """ Convert date and time information from the file's data to a Python list of datetime objects.

            Returned data structure:
            dt = a list of Python datetime objects

            Looks for these fields in this order:
                date/time,
                year/month/day/hour/minute/second,
                year/month/day/time,
                date/hour/minute/second,
                date_time,
                year/sdy/hour/minute/second,
                year/sdy/time,
                year/month/day/hour/minute,
                date/hour/minute,
                year/sdy/hour/minute,
                year/month/day/hour,
                date/hour,
                year/sdy/hour,
                year/month/day,
                date,
                year/sdy,
                start_date/start_time (headers),
                start_date (headers)
            in the SELF Python structure.
        """
        dt = []

        dateRegex = r"(\d{4})(\d{2})(\d{2})"
        timeRegex = r"(\d{1,2})\:(\d{2})\:(\d{2})(\.\d{1,6})?"

        if self.length == 0:
            raise ValueError(f'readSB.data structure is missing for file: {self.filename}')
            return

        if 'date'     in self.data and \
           'time'     in self.data:

            for d,t in zip([str(de) for de in self.data['date']],self.data['time']):
                da = re.search(dateRegex, d)
                ti = re.search(timeRegex, t)
                try:
                    if (ti.group(4) is not None):
                        millisecond = ti.group(4).replace(".","")
                    else:
                        millisecond = '0'
                    millisecond = self.millisecondToMicrosecond(millisecond)
                    dt.append(datetime(  # noqa: DTZ001
                        int(da.group(1)),
                        int(da.group(2)),
                        int(da.group(3)),
                        int(ti.group(1)),
                        int(ti.group(2)),
                        int(ti.group(3)),
                        int(millisecond)))
                except (ValueError, AttributeError) as e:
                    raise ValueError(
                        f'date/time fields not formatted correctly; unable to parse in file: {self.filename}'
                    ) from e

        elif 'year'   in self.data and \
             'month'  in self.data and \
             'day'    in self.data and \
             'hour'   in self.data and \
             'minute' in self.data and \
             'second' in self.data:
            second = [str(x).split('.')[0] for x in self.data['second']]
            millisecond = [self.millisecondToMicrosecond(str(x).split('.')[1]) if '.' in str(x) else 0 for x in self.data['second']]
            for y,m,d,h,mn,s,ms in zip(self.data['year'], self.data['month'], self.data['day'], self.data['hour'], self.data['minute'], second, millisecond):
                try:
                    dt.append(datetime(int(y), \
                                       int(m), \
                                       int(d), \
                                       int(h), \
                                       int(mn), \
                                       int(s), \
                                       int(ms)))  # noqa: DTZ001
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f'year/month/day/hour/minute/second fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'year'   in self.data and \
             'month'  in self.data and \
             'day'    in self.data and \
             'time'   in self.data:

            for y,m,d,t in zip(self.data['year'], self.data['month'], self.data['day'], self.data['time']):
                ti = re.search(timeRegex, t)
                try:
                    if (ti.group(4) is not None):
                        millisecond = ti.group(4).replace(".","")
                    else:
                        millisecond = '0'
                    millisecond = self.millisecondToMicrosecond(millisecond)
                    dt.append(datetime(int(y),  # noqa: DTZ001
                                       int(m),
                                       int(d),
                                       int(ti.group(1)),
                                       int(ti.group(2)),
                                       int(ti.group(3)),
                                        int(millisecond)))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'year/month/day/time fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'date'   in self.data and \
             'hour'   in self.data and \
             'minute' in self.data and \
             'second' in self.data:
            second = [str(x).split('.')[0] for x in self.data['second']]
            millisecond = [self.millisecondToMicrosecond(str(x).split('.')[1]) if '.' in str(x) else 0 for x in self.data['second']]
            for d,h,mn,s,ms in zip([str(de) for de in self.data['date']], self.data['hour'], self.data['minute'], second, millisecond):
                da = re.search(dateRegex, d)
                try:
                    dt.append(datetime(int(da.group(1)), # noqa: DTZ001
                                       int(da.group(2)),
                                       int(da.group(3)),
                                       int(h),
                                       int(mn),
                                       int(s),
                                        int(ms)))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'date/hour/minute/second fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'date_time' in self.data:

            for i in self.data('date_time'):
                da = re.search(r"{(\d{4})-(\d{2})-(\d{2})}\s(\d{1,2})\:(\d{2})\:(\d{2})(\.\d{1,6})?", i)
                try:
                    if (da.group(7) is not None):
                        millisecond = da.group(7).replace(".","")
                    else:
                        millisecond = '0'
                    millisecond = self.millisecondToMicrosecond(millisecond)
                    dt.append(datetime(  # noqa: DTZ001
                        int(da.group(1)),
                        int(da.group(2)),
                        int(da.group(3)),
                        int(da.group(4)),
                        int(da.group(5)),
                        int(da.group(6)),
                        int(millisecond)))  
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'date_time field not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'year'   in self.data and \
             'sdy'    in self.data and \
             'hour'   in self.data and \
             'minute' in self.data and \
             'second' in self.data:

            second = [str(x).split('.')[0] for x in self.data['second']]
            millisecond = [self.millisecondToMicrosecond(str(x).split('.')[1]) if '.' in str(x) else 0 for x in self.data['second']]
            for y,sdy,h,mn,s, ms in zip(self.data['year'], self.data['sdy'], self.data['hour'], self.data['minute'], second, millisecond):
                [m,d] = self.doy2mndy(y,sdy)
                try:
                    dt.append(datetime(int(y), # noqa: DTZ001
                                       int(m),
                                       int(d),
                                       int(h),
                                       int(mn),
                                       int(s),  
                                       int(millisecond)))
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f'year/sdy/hour/minute/second fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'year'   in self.data and \
             'sdy'    in self.data and \
             'time'   in self.data:

            for y,sdy,t in zip(self.data['year'], self.data['sdy'], self.data['time']):
                [m,d] = self.doy2mndy(y,sdy)
                ti = re.search(timeRegex, t)
                try:
                    if (ti.group(4) is not None):
                        millisecond = ti.group(4).replace(".","")
                    else:
                        millisecond = '0'
                    millisecond = self.millisecondToMicrosecond(millisecond)
                    dt.append(datetime(# noqa: DTZ001
                        int(y), 
                        int(m),
                        int(d),
                        int(ti.group(1)),
                        int(ti.group(2)),
                        int(ti.group(3)),
                        int(millisecond)))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'year/sdy/time fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'start_date' in self.headers and \
             'time'   in self.data:

            da = re.search(timeRegex, self.headers['start_date'])
            for t in self.data['time']:
                ti = re.search(dateRegex, t)
                try:
                    if (ti.group(4) is not None):
                        millisecond = ti.group(4).replace(".","")
                    else:
                        millisecond = '0'
                    millisecond = self.millisecondToMicrosecond(millisecond)
                    dt.append(datetime( # noqa: DTZ001
                        int(da.group(1)),  
                        int(da.group(2)),
                        int(da.group(3)),
                        int(ti.group(1)),
                        int(ti.group(2)),
                        int(ti.group(3)),
                        int(millisecond)))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'start_date header and time field not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'start_date' in self.headers and \
             'hour'   in self.data and \
             'minute' in self.data and \
             'second' in self.data:
            second = [str(x).split('.')[0] for x in self.data['second']]
            millisecond = [self.millisecondToMicrosecond(str(x).split('.')[1]) if '.' in str(x) else 0 for x in self.data['second']]
            da = re.search(dateRegex, self.headers['start_date'])
            for h,mn,s,ms in zip(self.data['hour'], self.data['minute'],second,millisecond):
                try:
                    dt.append(datetime(int(da.group(1)),  # noqa: DTZ001
                                       int(da.group(2)),
                                       int(da.group(3)),
                                       int(h),
                                       int(mn),
                                       int(s),
                                       int(ms)))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'start_date header and hour/minute/second field not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'year'   in self.data and \
             'month'  in self.data and \
             'day'    in self.data and \
             'hour'   in self.data and \
             'minute' in self.data:

            for y,m,d,h,mn in zip(self.data['year'], self.data['month'], self.data['day'], self.data['hour'], self.data['minute']):
                try:
                    dt.append(datetime(int(y),  # noqa: DTZ001
                                       int(m),
                                       int(d),
                                       int(h),
                                       int(mn),
                                       0))
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f'year/month/day/hour/minute fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'date'   in self.data and \
             'hour'   in self.data and \
             'minute' in self.data:

            for d,h,mn in zip([str(de) for de in self.data['date']], self.data['hour'], self.data['minute']):
                da = re.search(r"(\d{4})(\d{2})(\d{2})", d)
                try:
                    dt.append(datetime(  # noqa: DTZ001
                        int(da.group(1)),
                        int(da.group(2)),
                        int(da.group(3)),
                        int(h),
                        int(mn),
                        0
                    ))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'date/hour/minute fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'year'   in self.data and \
             'sdy'    in self.data and \
             'hour'   in self.data and \
             'minute' in self.data:

            for y, sdy, h, mn in zip(self.data['year'], self.data['sdy'], self.data['hour'], self.data['minute']):
                [m, d] = self.doy2mndy(y,sdy)
                try:
                    dt.append(datetime(int(y),  # noqa: DTZ001
                                       int(m),
                                       int(d),
                                       int(h),
                                       int(mn),
                                       0))
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f'year/sdy/hour/minute fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'year'   in self.data and \
             'month'  in self.data and \
             'day'    in self.data and \
             'hour'   in self.data:

            for y,m,d,h in zip(self.data['year'], self.data['month'], self.data['day'], self.data['hour']):
                try:
                    dt.append(datetime(int(y),  # noqa: DTZ001
                                       int(m),
                                       int(d),
                                       int(h),
                                       0,
                                       0))
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f'year/month/day/hour fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'date'   in self.data and \
             'hour'   in self.data:

            for d,h in zip([str(de) for de in self.data['date']], self.data['hour']):
                da = re.search(r"(\d{4})(\d{2})(\d{2})", d)
                try:
                    dt.append(datetime(int(da.group(1)),  # noqa: DTZ001
                                       int(da.group(2)),
                                       int(da.group(3)),
                                       int(h),
                                       0,
                                       0))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'date/hour fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'year'   in self.data and \
             'sdy'    in self.data and \
             'hour'   in self.data:

            for y,sdy,h in zip(self.data['year'], self.data['sdy'], self.data['hour']):
                [m,d] = self.doy2mndy(y,sdy)
                try:
                    dt.append(datetime(int(y),  # noqa: DTZ001
                                       int(m),
                                       int(d),
                                       int(h),
                                       0,
                                       0))
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f'year/sdy/hour fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'year'   in self.data and \
             'month'  in self.data and \
             'day'    in self.data:

            for y,m,d in zip(self.data['year'], self.data['month'], self.data['day']):
                try:
                    dt.append(datetime(int(y),  # noqa: DTZ001
                                       int(m),
                                       int(d),
                                       0,
                                       0,
                                       0))
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f'year/month/day fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'date'   in self.data:

            for d in zip([str(de) for de in self.data['date']]):
                da = re.search(dateRegex, d)
                try:
                    dt.append(datetime(  # noqa: DTZ001
                        int(da.group(1)),
                        int(da.group(2)),
                        int(da.group(3)),
                        0,
                        0,
                        0
                    ))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'date field not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'year'   in self.data and \
             'sdy'    in self.data:

            for y,sdy in zip(self.data['year'], self.data['sdy']):
                [m,d] = self.doy2mndy(y,sdy)
                try:
                    dt.append(datetime(  # noqa: DTZ001
                        int(y),
                        int(m),
                        int(d),
                        0,
                        0,
                        0
                    ))
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f'year/sdy fields not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'start_date' in self.headers and 'start_time' in self.headers:

            da = re.search(r"(\d{4})(\d{2})(\d{2})", self.headers['start_date'])
            ti = re.search(r"(\d{1,2})\:(\d{2})\:(\d{2})(\.\d{1,6})?\[(gmt|GMT)\]", self.headers['start_time'])
            for i in range(self.length):
                try:
                    if (ti.group(4) is not None):
                        millisecond = ti.group(4).replace(".","")
                    else:
                        millisecond = '0'
                    millisecond = self.millisecondToMicrosecond(millisecond)
                    dt.append(datetime(  # noqa: DTZ001
                        int(da.group(1)),
                        int(da.group(2)),
                        int(da.group(3)),
                        int(ti.group(1)),
                        int(ti.group(2)),
                        int(ti.group(3)),
                        int(millisecond)
                    ))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'/start_date and /start_time headers not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        elif 'start_date' in self.headers:
            da = re.search(dateRegex, self.headers['start_date'])
            for i in range(self.length):
                try:
                    dt.append(datetime(  # noqa: DTZ001
                        int(da.group(1)),
                        int(da.group(2)),
                        int(da.group(3)),
                        0,
                        0,
                        0
                    ))
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(
                        f'/start_date header not formatted correctly; unable to parse in file: {self.filename}. Error: {e}'
                    )

        else:
            print('Warning: fd_datetime failed -- file must contain a valid date and time information')

        return(dt)

#==========================================================================================================================================

    def addDataToOutput(self ,irow,var_name,units,var_value, overwrite):

        from copy import deepcopy

        #create empty column template for new var instantiation
        if not self.empty_col:
            for i in range(self.length):
                self.empty_col.append(str(self.missing))

        #handle the case where irow is used to extend the data matrix/concatenate files together
        if irow >= self.length:
            drow = irow - self.length
            for i in range(drow + 1):
                self.length = self.length + 1
                self.empty_col.append(str(self.missing))
                for var in self.data:
                    self.data[var].append(str(self.missing))

        #check for valid inputs
        if not var_value:
            var_value = str(self.missing)
        if not units:
            units = 'none'

        #define fields, units, and data column, if needed
        if var_name not in self.data:
            self.headers['fields'] = self.headers['fields'] + ',' + var_name
            try:
                self.headers['units'] = self.headers['units'] + ',' + units.lower()
            except KeyError:
                print('Warning: no units found in SeaBASS file header')
            self.data[var_name] = deepcopy(self.empty_col)

        #save data to column and row
        if self.is_number(self.data[var_name][irow]):
            if overwrite:
                self.data[var_name][irow] = var_value
            else:
                if float(self.data[var_name][irow]) == self.missing:
                    self.data[var_name][irow] = var_value
        else:
            if overwrite:
                self.data[var_name][irow] = var_value
            else:
                if str(self.missing) in self.data[var_name][irow]:
                    self.data[var_name][irow] = var_value

#==========================================================================================================================================

    def writeSBfile(self, ofile):
        """
        writeSBfile writes out an SeaBASS file
        given an output file name
        syntax: SELF.writeSBfile(ofile)
        """
        from math import isnan

        with open(ofile, 'w') as fout:
            fout.write('/begin_header\n')

        # Headers
        for header in self.headers:  # noqa: FURB122
            fout.write(f'/{header}={self.headers[header]}\n')

        # Comments
        for comment in self.comments:  # noqa: FURB122
            fout.write(f'!{comment}\n')

        fout.write('/end_header\n')

        if   'comma' in self.headers['delimiter']:
            delim = ','
        elif 'space' in self.headers['delimiter']:
            delim = ' '
        elif 'tab'   in self.headers['delimiter']:
            delim = '\t'

        for i in range(self.length):
            row_ls = []

            for var in self.data:

                if self.is_number(self.data[var][i]):
                    if float(self.data[var][i]) == float(self.missing) or isnan(float(self.data[var][i])):
                        row_ls.append(str(self.missing))
                    else:
                        row_ls.append(str(self.data[var][i]))
                else:
                    if str(self.missing) in self.data[var][i] or 'nan' in self.data[var][i].lower():
                        row_ls.append(str(self.missing))
                    else:
                        row_ls.append(str(self.data[var][i]))

            fout.write(delim.join(row_ls) + '\n')

        fout.close()
