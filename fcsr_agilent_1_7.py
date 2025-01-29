#!/usr/bin/env python3

"""Find, copy, sort, rename
Finds and sorts agilent .d folders according to the sample name in the
ch1.uv file
"""


import re # Für Regex-Suche
import os # für allgemeine dateimanipulationen
import shutil #für ordner-kopieren
import configparser # configfile für start, ziel und subfoldernamen
import logging #für Logging
import sys


def findSubfolderName(regexInitials, sampleNameString, folderNoInitials, initialsList):
    if regexInitials == '':
        print('No valid initials found in sample name: ' + sampleNameString)
        logging.info('No valid initials found in sample name: ' + sampleNameString)
        return folderNoInitials
    
    print('Found initials: ' + regexInitials)
    logging.info('Found initials: ' + regexInitials)
    
    #Compare initials to initialsList and return matches
    regexInitialsList = re.compile(regexInitials, re.IGNORECASE) #damit sample names xy, XY und Xy alle in den Ordner Xy gehen
    subfolderList = [m.group(0) for initial in initialsList for m in [regexInitialsList.search(initial)] if m] #gibt ergebnisliste mit einem Element aus
    subfolder = ''.join(subfolderList) #konvertiert Liste in String // Might be problematic, if the list contains the match multiple times
    if subfolder == '':
        return folderNoInitials
    return subfolder

def copyFolderToDestination(parentFolder, destinationPath, subfolder, sampleNameString, instrumentSuffix):
    """Ordner in den entsprechenden subfolder verschieben, gucken, dass nichts überschrieben wird"""
    try:
        shutil.copytree(parentFolder, os.path.join(destinationPath, subfolder, (sampleNameString + ' ' + instrumentSuffix + '.d')))
        print('Saved in subfolder: ' + subfolder + ' as: ' + sampleNameString + ' ' + instrumentSuffix + '.d')
        logging.info('Saved in subfolder: ' + subfolder + ' as: ' + sampleNameString + ' ' + instrumentSuffix + '.d')
    except FileExistsError: #wenn es den Ordner schon gibt...
        print('Folder ' + sampleNameString + ' ' + instrumentSuffix + '.d already exists, retrying.')
        logging.info('Folder ' + sampleNameString + ' ' + instrumentSuffix + '.d already exists, retrying.')
        copynumber = 0
        while True:
            copynumber = copynumber + 1
            try: #... dann wird an den Ordnernamen erst xyz-1.d, dann xyz-2.d etc. angehängt, bis ein neuer Ordnername gefunden wurde
                shutil.copytree(parentFolder, os.path.join(destinationPath, subfolder, (sampleNameString + '-' + str(copynumber) + ' ' + instrumentSuffix + '.d')))
                print('Saved in subfolder: ' + subfolder + ' as: ' + sampleNameString + '-' + str(copynumber) + ' ' + instrumentSuffix + '.d')
                logging.info('Saved in subfolder: ' + subfolder + ' as: ' + sampleNameString + '-' + str(copynumber) + ' ' + instrumentSuffix + '.d')
                break
            except FileExistsError:
                print('Folder ' + sampleNameString + '-' + str(copynumber) + ' ' + instrumentSuffix + '.d already exists, retrying.')
                logging.info('Folder ' + sampleNameString + '-' + str(copynumber) + ' ' + instrumentSuffix + '.d already exists, retrying.')
                continue

def walklevel(some_dir, level=1):
    """Wie os.walk, aber wird nach einer bestimmten Suchtiefe abgebrochen"""
    some_dir = some_dir.rstrip(os.path.sep)
    try:
        assert os.path.isdir(some_dir)
    except AssertionError:
        print(f'The source path {sourcePath} does not exist.')
        logging.error(f'The source path {sourcePath} does not exist.')
        sys.exit(1)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]

if __name__ == "__main__":

    #Setup logging
    logging.basicConfig(format='%(asctime)s %(message)s',filename=r'fcsr_agilent.log',level=logging.DEBUG)
    logging.info('Program started.')

    #Ini-File Öffnen
    configparser = configparser.RawConfigParser()
    configFilePath = r'fcsr_agilent.ini' #die .ini soll im selben Ordner liegen wie fcsr_agilent.py
    configparser.read(configFilePath)
    #Pfade aus datei einlesen
    sourcePath = configparser.get('paths', 'sourcePath')
    destinationPath = configparser.get('paths', 'destinationPath')
    #Liste der Initialen aus datei einlesen
    initialsList = [e.strip() for e in configparser.get('initials', 'initialsList').split(',')]
    #Zielordner für Files einlesen, die sich nicht zuordnen lassen
    folderNoInitials = configparser.get('initials', 'folderNoInitials')
    #Suchtiefe einlesen
    searchDepth = int(configparser.get('parameters', 'searchDepth'))
    #Bezeichnung des Geräts für Filename einlesen (xy 1234 ESI, xy 1234 GCMS, ...)
    instrumentSuffix = configparser.get('parameters', 'instrumentSuffix')

    #Zielordner anlegen, wenn noch nicht vorhanden
    for initials in initialsList:
        os.makedirs(os.path.join(destinationPath, initials), exist_ok = True)

    #Liste der bereits verarbeiteten Läufe einlesen
    try:
        with open(r'processed_folders.txt', 'r') as procFolders:
            procFoldersList = procFolders.read().splitlines()
    except FileNotFoundError:
        print('processed_folders.txt does not exist, creating it...')
        logging.info('processed_folders.txt does not exist, creating it...')
        with open(r'processed_folders.txt', "w") as file:
            pass  # Just create an empty file
        with open(r'processed_folders.txt', 'r') as procFolders:
            procFoldersList = procFolders.read().splitlines()



    # alternative regex ([a-zA-Z]{2,3})(?: .|\d)
    sampleNameRegex = re.compile(r'''(
        (^[a-zA-Z]{2,3}) # Initialen am Beginn des Filenames (2-3 Buchstaben)
        (?: .|\d) #Leerzeichen gefolgt von Buchstaben oder kein Leerzeichen gefolgt von Zahlen
        )''', re.VERBOSE|re.IGNORECASE)

    #Find folder names (xyz.d) and *.uv file (dad1.uv)

    for tops, dirs, files in walklevel(sourcePath,searchDepth):
        level = tops.count(os.sep) - sourcePath.count(os.sep)
        for file in files:
            if file.lower().endswith("dad1.uv"):
                level = tops.count(os.sep) - sourcePath.count(os.sep)
                if level <= searchDepth:
                    if tops in procFoldersList:
                        print('Found folder: ' + (tops) + '. Already processed. Skipping...')
                        logging.info('Found folder: ' + (tops) + '. Already processed. Skipping...')
                    elif os.path.isfile(os.path.join(tops, 'ACQRES.REG')) is False:
                        print('Found folder: ' + (tops) + '. Run in progress. Skipping...')
                        logging.info('Found folder: ' + (tops) + '. Run in progress. Skipping...')
                    else:
                        print('Found folder: ' + (tops) + '. Trying to open file: ' + (file))
                        logging.info('Found folder: ' + (tops) + '. Trying to open file: ' + (file))
                        #Sample name string in *.uv finden
                        sourceFileLocation = os.path.join(tops, file)
                        with open(sourceFileLocation, encoding ="cp1252", errors ='ignore') as sourceFile:
                            sourceFile.read(858) #discards the first 858 bytes // maybe use seek?
                            sampleNameRawString = sourceFile.read(120) #reads the next 120 bytes (that's where the sample name is)

                        print('Found sample name: ' + sampleNameRawString)
                        logging.info('Found sample name: ' + sampleNameRawString)

                        #Clean up the string so it is suitable as file name
                        sampleNameString = sampleNameRawString.replace('\x00', "").strip() #removes all "null" characters and deletes the whitespace
                        sampleNameString = re.sub(r'(?u)[+]', 'plus', sampleNameString) #substitutes illegal character +
                        sampleNameString = re.sub(r'(?u)[=]', 'eq', sampleNameString) #substitutes illegal character =
                        sampleNameString = re.sub(r'(?u)[°]', 'deg', sampleNameString) #substitutes illegal character °
                        sampleNameString = re.sub(r'(?u)[^-\w\s.]', '', sampleNameString) #removes all special characters except -,.,and space
                        sampleNameString = sampleNameString[:30] #truncates string to 30 characters

                        if sampleNameString == '':
                            sampleNameString = 'unnamed'
                            print('This would generate a blank folder name, renamed to: ' + sampleNameString)
                            logging.info('This would generate a blank folder name, renamed to: ' + sampleNameString)
                        else:
                            print('Generated new folder name: ' + sampleNameString)
                            logging.info('Generated new folder name: ' + sampleNameString)

                        #Find Initials in sampleNameString
                        regexInitials = '' #regexInitials hat zunächst keine Treffer
                        for groups in sampleNameRegex.findall(sampleNameString): #jetzt wird gesucht
                            regexInitials = groups[1] #Die Initialen gehen in den String regexInitials // may need to use index 0 without the outer capture group
                            break

                        #inserts a space between Initials and Rest of Sample Name by first removing the Initials, then stripping preceding whitespace, then re-entering initials and a Space
                        sampleNameString = (regexInitials + ' ' + (re.sub(regexInitials, '', sampleNameString, 1, re.IGNORECASE)).strip())

                        subfolder = findSubfolderName(regexInitials, sampleNameString, folderNoInitials, initialsList)
                        print('Run will be saved in subfolder: ' + subfolder)
                        logging.info('Run will be saved in subfolder: ' + subfolder)

                        copyFolderToDestination(tops, destinationPath, subfolder, sampleNameString, instrumentSuffix)
                        #verarbeiteten Ordner an die 'processed_folders.txt' anhängen
                        with open(r'processed_folders.txt', 'a') as procFolders:
                            procFolders.write(tops + '\n')
                    print('')
                    logging.info('')

    #Schleife beendet, nächsten Folder finden
    print('Program finished.')
    logging.info('Program finished.')
