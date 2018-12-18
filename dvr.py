import pandas as pd
import requests, bs4, re, json, pickle
import numpy as np

def getHtml(filmUrl):
    res = requests.get(filmUrl)
    res.raise_for_status()
    return res

def parseHtml(res):
    soup = bs4.BeautifulSoup(res.text, "lxml")
    return soup

def grabYearCastUrl(i):
    year = JS["movies"][i]["year"]
    cast = JS["movies"][i]["castItems"][0]["name"]
    urlTag = JS["movies"][i]["url"]
    return year, cast, urlTag

def grabFilmDuration(res):
    durationPattern = re.compile(r"\d{2,4} minutes")
    soup = bs4.BeautifulSoup(res.text, "lxml")
    soup = soup.find("ul", class_="content-meta info")
    soup = soup.getText()
    minutes = re.search(durationPattern, soup)
    minutes = minutes.group().partition(' ')[0]
    return minutes


rtUrl = r"https://www.rottentomatoes.com"
rtSearchUrl = r"https://www.rottentomatoes.com/search/?search="

# load excel into DF obj
df = pd.read_excel(r"dvr_pandas.xlsx", sheet_name="Sheet1")
df["Films"] = df["Films"].str.strip()

# make film title http friendly
df.replace('\s+', '_', regex=True, inplace=True)
df.dropna(subset=['Films'], inplace=True)

filmsNotFound = []
# don't need this; maybe launch rt page search that failed

minutesList = []
# store all scraped film durations in here; we'll populate the duration column after running loop

nanSum = df.Time.isnull().sum()
nanStartIndex = len(df.Time) - nanSum

for film in df.loc[nanStartIndex:, "Films"]:
    # only search for values you don't already have
    try:
        # see if the film name added to url works directly
        filmUrl = rtUrl + "/m/" + str(film)

        res = getHtml(filmUrl)
        soup = parseHtml(res)
        minutes = grabFilmDuration(res)
        if minutes != None:
            minutesList.append(minutes)
        else:
            minutes = np.nan
            minutesList.append(minutes)
        # update second column with minutes

    except:
        # http error
        try:
            # search for film title; try because it's possible that you return no results
            searchFilm = re.sub("_", "%20", film)
            filmUrl2 = rtSearchUrl + str(searchFilm)

            res = getHtml(filmUrl2)
            soup = parseHtml(res)

            # isolate js dict function
            JS = soup.find("div", id="main_container")
            yearPattern = re.compile(r"\d{4},")
            dictPattern = re.compile(r'{"actorCount".+"tvCount".+}')
            JS = JS.find("script").getText()
            JS = re.search(dictPattern, JS).group()
            JS = json.loads(JS)

            for i in range(3):
                try:
                    year, cast, urlTag = grabYearCastUrl(i)

                    filmValidation = input("{}, the {} film starring {}? (y/n)\n".format(film, year, cast))

                    if filmValidation == "y":
                        filmUrl = rtUrl + urlTag
                        res = getHtml(filmUrl)
                        soup = parseHtml(res)
                        minutes = grabFilmDuration(res)
                        # print(film + ": " + minutes)
                        if minutes != None:
                            minutesList.append(minutes)
                        else:
                            minutes = np.nan
                            minutesList.append(minutes)
                        break

                    elif filmValidation == "n":
                        if i == 2:
                            filmsNotFound.append(film)
                            # print(filmsNotFound)
                            minutes = np.nan
                            minutesList.append(minutes)
                        continue

                except IndexError as ie:
                    filmsNotFound.append(film)
                    # print(filmsNotFound)
                    minutes = np.nan
                    minutesList.append(minutes)
                    break

        except:
            # http error
            filmsNotFound.append(film)
            # print(filmsNotFound)
            minutes = np.nan
            minutesList.append(minutes)

        # i could also automatically run checks on ebert for star rating (3 or greater) and imdb
        # make film title bold if 4 stars from ebert
        # append films that don't make the cut to a list (with plot from imdb), so I can manually delete them from DVR

        # use multiprocessing or threading (both!) to speed up

df.loc[nanStartIndex:, "Time"] = minutesList

df.Time = pd.to_numeric(df.Time, errors='coerce')
df.sort_values(by=('Time'), ascending=False, inplace=True)

df.replace('_', ' ', regex=True, inplace=True)

writer = pd.ExcelWriter('dvr_pandas.xlsx', engine='xlsxwriter')
df.to_excel(writer, sheet_name='Sheet1', index=False)

workbook = writer.book
worksheet = writer.sheets['Sheet1']
worksheet.set_column('A:A', 26)
writer.save()

# If you want to pickle it, do the following. But I'm just going to read the exel
# pickle_out = open("dvr.pickle", "wb")
# pickle.dump(df, pickle_out)
# pickle_out.close()