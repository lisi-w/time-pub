import mapfile as mp
import mk_dataset as mkd
import update as up
import pub_test as pt
import pid_cite_pub as pid
import os
import json
import sys
import tempfile
from cmip6_cv import PrePARE
from settings import *


def prepare_internal(json_map, cmor_tables):
    print("iterating through filenames for PrePARE (internal version)...")
    validator = PrePARE.PrePARE
    for info in json_map:
        filename = info[1]
        process = validator.checkCMIP6(cmor_tables)
        process.ControlVocab(filename)


def check_files(files):
    for file in files:
        try:
            myfile = open(file, 'r')
        except Exception as ex:
            print("Error opening file " + file + ": " + str(ex))
            exit(1)
        myfile.close()


def exit_cleanup(scan_file):
    scan_file.close()


def wrapper(func, *args, **kwargs):
    def wrapped():
        return func(*args, **kwargs)
    return wrapped


def autocuratorf(autoc_command, fullmap, scanfn):
    os.system("bash gen-five/src/python/autocurator.sh " + autoc_command + " " + fullmap + " " + scanfn)


def main(fullmap):

    split_map = fullmap.split("/")
    fname = split_map[-1]
    fname_split = fname.split(".")
    proj = fname_split[0]
    cmip6 = False
    if proj == "CMIP6":
        cmip6 = True

    files = []
    files.append(fullmap)

    check_files(files)

    cert = CERT_FN

    scan_file = tempfile.NamedTemporaryFile()  # create a temporary file which is deleted afterward for autocurator
    scanfn = scan_file.name  # name to refer to tmp file

    # add these as command line args
    autocurator = AUTOC_PATH

    autoc_command = autocurator + "/bin/autocurator"  # concatenate autocurator command

    os.system("cert_path=" + cert)

    print("Converting mapfile...")
    try:
        mymap = wrapper(mp.main, [fullmap, proj])
        print("TIME: " + str(timeit.timeit(mymap, number=1)))
        map_json_data = mp.main([fullmap, proj])
    except Exception as ex:
        print("Error with converting mapfile: " + str(ex))
        exit_cleanup(scan_file)
        exit(1)
    print("Done.")

    # Run autocurator and all python scripts
    print("Running autocurator...")
    autoc = wrapper(autocuratorf, autoc_command, fullmap, scanfn)
    print("TIME: " + str(timeit.timeit(autoc, number=1)))
    os.system("bash gen-five/src/python/autocurator.sh " + autoc_command + " " + fullmap + " " + scanfn)

    print("Done.\nMaking dataset...")
    try:
        makedata = wrapper(mkd.main, [map_json_data, scanfn])
        print("TIME: " + str(timeit.timeit(makedata, number=1)))
        out_json_data = mkd.main([map_json_data, scanfn])

    except Exception as ex:
        print("Error making dataset: " + str(ex))
        exit_cleanup(scan_file)
        exit(1)

    if cmip6:
        print("Done.\nRunning pid cite...")
        try:
            pidc = wrapper(pid.main, out_json_data)
            print("TIME: " + str(timeit.timeit(pidc, number=1)))
            new_json_data = pid.main(out_json_data)
        except Exception as ex:
            print("Error running pid cite: " + str(ex))
            exit_cleanup(scan_file)
            exit(1)

    print("Done.\nUpdating...")
    try:
        upd = wrapper(up.main, new_json_data)
        print("TIME: " + str(timeit.timeit(upd, number=1)))
        up.main(new_json_data)
    except Exception as ex:
        print("Error updating: " + str(ex))
        exit_cleanup(scan_file)
        exit(1)

    print("Done.\nRunning pub test...")
    try:
        pubt = wrapper(pt.main, out_json_data)
        print("TIME: " + str(timeit.timeit(pubt, number=1)))
        pt.main(new_json_data)
    except Exception as ex:
        print("Error running pub test: " + str(ex))
        exit_cleanup(scan_file)
        exit(1)

    print("Done. Cleaning up.")
    exit_cleanup(scan_file)


if __name__ == '__main__':

    fullmap = sys.argv[2]  # full mapfile path
    # allow handling of multiple mapfiles later
    if fullmap[-4:] != ".map":
        myfile = open(fullmap)
        for line in myfile:
            length = len(line)
            main(line[0:length-2])
        myfile.close()
        # iterate through file in directory calling main
    else:
        main(fullmap)
