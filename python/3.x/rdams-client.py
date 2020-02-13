#!/usr/bin/env python
"""List dataset metadata, subset data subset requests,
check on request status.

Usage:
```
rdams-client.py -get_summary <dsnnn.n>
rdams-client.py -get_metadata <dsnnn.n> <-f>
rdams-client.py -get_param_summary <dsnnn.n> <-f>
rdams-client.py -submit [control_file_name]
rdams-client.py -get_status <RequestIndex> <-proc_status>
rdams-client.py -download [RequestIndex]
rdams-client.py -globus_download [RequestIndex]
rdams-client.py -get_control_file_template <dsnnn.n>
rdams-client.py -help
```
"""
__version__ = '0.2'
__author__ = 'Doug Schuster (schuster@ucar.edu), Riley Conroy (rpconroy@ucar.edu)'

import pdb
import sys
import os
import urllib.request
import urllib.error
import urllib.parse
import getpass
import http.cookiejar
import json
import argparse

def update_progress(progress, outdir):
    """Displays or updates a console progress bar

    Accepts a float between 0 and 1. Any int will be converted to a float.
    A value under 0 represents a 'halt'.
    A value at 1 or bigger represents 100%
    """
    barLength = 20  # Modify this to change the length of the progress bar
    status = ""
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float\r\n\n"
    if progress < 0:
        progress = 0
        status = "Halt...\r\n\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n\n"
    block = int(round(barLength * progress))
    text = "\rDownloading Request to './{0}' directory.  Download Progress: [{1}] {2}% {3}".format(
        outdir, "=" * block + " " * (barLength - block), progress * 100, status)
    sys.stdout.write(text)
    sys.stdout.flush()

def download_file(remfile, outfile):
    """Download a file from a remote server (remfile) to a local location (outfile)."""
    frequest = urllib.request.Request(remfile)
    fresponse = urllib.request.urlopen(remfile)
    with open(outfile, 'wb') as handle:
        handle.write(fresponse.read())

def add_ds_str(ds_num):
    """Adds 'ds' to ds_num if needed.
    Throws error if ds number isn't valid.
    """
    ds_num = ds_num.strip()
    if ds_num[0:2] != 'ds':
        ds_num = 'ds' + ds_num
    if len(ds_num) != 7:
        print("'" + ds_num + "' is not valid.")
        sys.exit()
    return ds_num

def get_userinfo():
    """Get username and password."""
    user = input("Enter your RDA username or email: ")
    pasw = getpass.getpass("Enter your RDA password: ")
    return(user, pasw)

def add_http_auth(url, user, pasw):
    """Add authentication information to opener and return opener."""
    passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, theurl, username, password)
    authhandler = urllib.request.HTTPBasicAuthHandler(passman)
    opener = urllib.request.build_opener(authhandler)
    urllib.request.install_opener(opener)
    return opener

def add_http_cookie(url, authstring):
    """Get and add authentication cookie to http file download handler."""
    cj = http.cookiejar.MozillaCookieJar(cookie_file)
    openrf = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj))
    frequest = urllib.request.Request(url, authstring)
    cj.add_cookie_header(frequest)
    response = openrf.open(frequest)
    openerf = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj))
    urllib.request.install_opener(openerf)

def write_pw_file(pwfile, username, password):
    """Write out file with user information."""
    with open(pwfile, "w") as fo:
        npwstring = username + ',' + password
        fo.write(npwstring)

def read_pw_file(pwfile):
    """Read user information from pw file."""
    with open(pwfile, 'r') as f:
        pwstring = f.read()
        (username, password) = pwstring.split(',', 2)
    return(username, password)

def download_files(filelist, directory):
    """Download multiple files from the rda server and save them to a local directory."""
    backslash = '/'
    filecount = 0
    percentcomplete = 0
    localsize = ''
    length = 0
    length = len(filelist)
    if not os.path.exists(directory):
        os.makedirs(directory)
    for key, value in filelist.items():
        downloadpath, localfile = key.rsplit("/", 1)
        outpath = directory + backslash + localfile
        percentcomplete = (float(filecount) / float(length))
        update_progress(percentcomplete, directory)
        if os.path.isfile(outpath):
            localsize = os.path.getsize(outpath)
            if(str(localsize) != value):
                download_file(key, outpath)
        elif(not os.path.isfile(outpath)):
            download_file(key, outpath)

        filecount = filecount + 1
        percentcomplete = (float(filecount) / float(length))
    update_progress(percentcomplete, directory)


def get_parser():
    """Creates and returns parser object."""
    description = "Queries NCAR RDA REST API."
    parser = argparse.ArgumentParser(prog='rdams', description=description)
    parser.add_argument('-get_summary', '-g',
            type=str,
            metavar='<dsid>',
            required=False,
            help="Get a summary of the given dataset.")
    parser.add_argument('-get_metadata', '-gm',
            type=str,
            metavar='<dsid>',
            required=False,
            help="Get metadata for a given dataset")
    parser.add_argument('-get_param_summary', '-gpm',
            type=str,
            metavar='<dsid>',
            required=False,
            help="Get only parameters for a given dataset")
    parser.add_argument('-submit', '-s',
            type=str,
            metavar='<dsid>',
            required=False,
            help="Submit a request using a control file")
    parser.add_argument('-get_status', '-gs',
            type=str,
            metavar='<Control filename>',
            required=False,
            help="Get a summary of the given dataset.")
    parser.add_argument('-download', '-d',
            type=str,
            required=False,
            metavar='<Request Index>',
            help="Download data given a request id")
    parser.add_argument('-globus_download', '-gd',
            type=str,
            required=False,
            metavar='<Request Index>',
            help="Start a globus transfer for a give request index.")
    parser.add_argument('-get_control_file_template', '-gt',
            type=str,
            metavar='<dsid>',
            required=False,
            help="Get a template control file used for subsetting")
    return parser

def get_summary(ds):
    """Returns summary of dataset.

    Args:
        ds (str): Datset id. e.g. 'ds083.2'

    Returns:
        dict: JSON decoded result of the query.
    """

    pass

def get_metadata(ds):
    """Return metadata of dataset.

    Args:
        ds (str): Datset id. e.g. 'ds083.2'

    Returns:
        dict: JSON decoded result of the query.
    """
    pass

def get_param_summary(ds):
    """Return summary of parameters for a dataset.

    Args:
        ds (str): Datset id. e.g. 'ds083.2'

    Returns:
        dict: JSON decoded result of the query.
    """
    pass

def submit(control_file_name):
    """Subit a RDA subset or format conversion request.

    Args:
        control_file_name (str): control file to submit.

    Returns:
        dict: JSON decoded result of the query.
    """
    pass

def get_status(request_idx):
    """Get status of request.

    Args:
        request_idx (str): Request Index, typcally a 6-digit int.

    Returns:
        dict: JSON decoded result of the query.
    """
    pass

def download(request_idx):
    """Return summary of parameters for a dataset.

    Args:
        ds (str): datset id. e.g. 'ds083.2'

    Returns:
        dict: JSON decoded result of the query.
    """
    pass

def globus_download(request_idx):
    """Return summary of parameters for a dataset.

    Args:
        ds (str): datset id. e.g. 'ds083.2'

    Returns:
        dict: JSON decoded result of the query.
    """
    pass

def get_control_file_template(ds):
    """Return summary of parameters for a dataset.

    Args:
        ds (str): datset id. e.g. 'ds083.2'

    Returns:
        dict: JSON decoded result of the query.
    """
    pass

def query(args):
    """Perform a query based on command line like arguments.
    """
    parser = get_parser()
    if len(args) == 1:
        parser.parse_args(['-h'])
        exit(1)
    args = parser.parse_args(args)
    exit()

    sys.tracebacklimit = 0
    base = 'https://rda.ucar.edu/apps/'
    jsondata = ''
    username = ''
    password = ''
    pwfile = './rdamspw.txt'
    pwstring = ''
    npwstring = ''
    controlfile = ''
    controlparms = {}
    cookie_file = 'auth.rda_ucar_edu'
    loginurl = 'https://rda.ucar.edu/cgi-bin/login'
    exitstring = "\nUsage: \nrdams-client.py -get_summary <dsnnn.n>\nrdams-client.py -get_metadata <dsnnn.n>\nrdams-client.py -get_param_summary <dsnnn.n>\nrdams-client.py -submit [control_file_name]\nrdams-client.py -get_status <RequestIndex> <-proc_status>\nrdams-client.py -download [RequestIndex]\nrdams-client.py -globus_download [RequestIndex]\nrdams-client.py -purge [RequestIndex]\nrdams-client.py -get_control_file_template <dsnnn.n>\nrdams-client.py -help\n\n"

    if len(sys.argv) > 1:
        if sys.argv[1] == "-get_summary":
            print('\nGetting summary information.  Please wait as this may take awhile.\n')
            theurl = base + 'summary'
            if len(sys.argv) > 2:
                theurl = base + 'summary/' + add_ds_str(sys.argv[2])
        elif sys.argv[1] == "-get_metadata":
            print('\nGetting metadata.  Please wait as this may take awhile.\n')
            theurl = base + 'metadata'
            if len(sys.argv) == 3:
                theurl = base + 'metadata/' + add_ds_str(sys.argv[2])
            elif len(sys.argv) == 4:
                theurl = base + 'metadata/' + add_ds_str(sys.argv[2]) + '/formatted'
        elif sys.argv[1] == "-get_param_summary":
            print('\nGetting parameter summary.  Please wait as this may take awhile.\n')
            theurl = base + 'paramsummary'
            if len(sys.argv) == 3:
                theurl = base + 'paramsummary/' + add_ds_str(sys.argv[2])
            elif len(sys.argv) == 4:
                theurl = base + 'paramsummary/'+ add_ds_str(sys.argv[2]) + '/formatted'
        elif sys.argv[1] == "-help":
            theurl = base + 'help'
        elif sys.argv[1] == "-get_control_file_template":
            theurl = base + 'template'
            controlfile = './dsnnn.n_control_file'
            if len(sys.argv) > 2:
                theurl = base + 'template/' + add_ds_str(sys.argv[2])
                controlfile = './' + add_ds_str(sys.argv[2]) + '_control_file'
        elif sys.argv[1] == "-get_status":
            theurl = base + 'request'
            if len(sys.argv) == 3:
                theurl = base + 'request/' + sys.argv[2]
            elif len(sys.argv) == 4:
                theurl = base + 'request/' + sys.argv[2] + '/' + add_ds_str(sys.argv[3])
        elif sys.argv[1] == "-download":
            if len(sys.argv) > 2:
                theurl = base + 'request/' + sys.argv[2] + '/filelist'
            else:
                sys.exit("\nUsage: \nrdams-client.py -download [RequestIndex]\n")
        elif sys.argv[1] == "-globus_download":
            if len(sys.argv) > 2:
                theurl = base+'request/' + sys.argv[2] + '/-globus_download'
            else:
                sys.exit("\nUsage: \nrdams-client.py -globus_download [RequestIndex]\n")
        elif sys.argv[1] == "-purge":
            if len(sys.argv) > 2:
                theurl = base + 'request/' + sys.argv[2]
            else:
                sys.exit("\nUsage: \nrdams-client.py -purge [RequestIndex]\n")
        elif sys.argv[1] == "-submit":
            if len(sys.argv) > 2:
                theurl = base + 'request'
                with open(sys.argv[2], "r") as myfile:
                    for line in myfile:
                        if line.startswith('#'):
                            continue
                        li = line.rstrip()
                        (key, value) = li.split('=', 2)
                        controlparms[key] = value
                jsondata = '{'
                for k in list(controlparms.keys()):
                    jsondata += '"' + k + '"' + ":" + '"' + controlparms[k] + '",'
                jsondata = jsondata[:-1]
                jsondata += '}'
                print('\nSubmitting request.  Please wait as this may take awhile.\n')
            else:
                sys.exit(
                    "\nUsage: \nrdams-clientpy -submit [control_file_name]\n")
        else:
            sys.exit(exitstring)
    else:
        sys.exit(exitstring)


    if os.path.isfile(pwfile) and os.path.getsize(pwfile) > 0:
        (username, password) = read_pw_file(pwfile)
    else:
        (username, password) = get_userinfo()
    opener = add_http_auth(theurl, username, password)

    if len(jsondata) > 1:
        request = urllib.request.Request(
            theurl, jsondata.encode(), {'Content-type': 'application/json'})
    else:
        request = urllib.request.Request(theurl)

    if sys.argv[1] == "-purge":
        request.get_method = lambda: 'DELETE'

    try:
        url = opener.open(request)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print('RDA username and password invalid.  Please try again\n')
            (username, password) = get_userinfo()
            opener = add_http_auth(theurl, username, password)
            try:
                url = opener.open(request)
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    print(
                        'RDA username and password invalid, or you are not authorized to access this dataset.\n')
                    print('Please verify your login information at http://rda.ucar.edu\n.')
                    sys.exit()


    write_pw_file(pwfile, username, password)


    if sys.argv[1] == "-get_control_file_template":
        print('\nWriting example control file to ' + controlfile + '\n')
        with open(controlfile, "wb") as fo:
            fo.write(url.read())
        sys.exit()
    if sys.argv[1] == "-download":
        authdata = 'email=' + username + '&password=' + password + '&action=login'
        authdata = authdata.encode()

        jsonfilelist = url.read().decode()

        if jsonfilelist[0] != "{":
            print(jsonfilelist)
            sys.exit()

        filelist = json.loads(jsonfilelist)
        length = len(filelist)

        directory = 'rda_request_' + sys.argv[2]

        # get cookie required to download data files
        add_http_cookie(loginurl, authdata)

        print("\n\nStarting Download.\n\n")

        download_files(filelist, directory)

        sys.exit()

    print(url.read().decode())

if __name__ == "__main__":
    """Calls Generic main method"""
    query(sys.argv)
