import sys
import ccxt
import yaml
import os
import re
import datetime
import pytz
import time
# Import base class
from .basic import Basic
# Import enrichments
from aitblib import enrichments
# SQL alchemy
from sqlalchemy import Column
from sqlalchemy import Integer, Float
from sqlalchemy.schema import CreateTable
from sqlalchemy.ext.declarative import declarative_base
# Dataframes
import pandas as pd
import numpy as np


class Helper(Basic):

    def test(self):
        print('########################', file=sys.stderr)
        print('Testing Helper Class', file=sys.stderr)
        print('########################', file=sys.stderr)

    def createCryptoCon(self, ex):
        # Create temp Exchange
        ex_class = getattr(ccxt, ex)
        tmpex = ex_class()
        markets = tmpex.load_markets()
        # Fees and Quotes
        feesdict = {}
        quotes = []
        fees = []
        # Itterate through crypto markets
        for symb in markets:
            if markets[symb]['taker']:
                feesdict.update({str(symb): markets[symb]['taker']})
                fees.append(markets[symb]['taker'])
            quotes.append(markets[symb]['quote'])
        # Mode fees
        from statistics import mode
        tmpfeesmode = mode(fees)
        # Find unique quotes and join them
        tmpquotes = ', '.join(set(quotes))
        # Fees creations
        tmpfees = {'fees': feesdict}
        # Join time frames
        try:
            tmptf = ', '.join(tmpex.timeframes.keys())
        except BaseException:
            tmptf = 'N/A'
        # Check for multiple countries
        try:
            tmpco = ', '.join(tmpex.countries)
        except BaseException:
            tmpco = 'N/A'
        # Check pairs and symbols
        tmppairs = ', '.join(tmpex.symbols)
        # Make abilities sub
        abilities = {'abilities': tmpex.has}
        # Create Connection YAML
        conYML = 'id: ' + tmpex.id + "\n"
        conYML = conYML + 'name: ' + tmpex.name + "\n"
        conYML = conYML + 'type: CryptoCurrency' + "\n"
        conYML = conYML + 'certified: ' + str(tmpex.certified).lower() + "\n"
        conYML = conYML + 'timeframes: ' + tmptf + "\n"
        conYML = conYML + 'timeout: ' + str(tmpex.timeout) + "\n"
        conYML = conYML + 'ratelimit: ' + str(tmpex.rateLimit) + "\n"
        conYML = conYML + 'countries: ' + tmpco + "\n"
        conYML = conYML + 'quotes: ' + tmpquotes + "\n"
        conYML = conYML + 'pairs: ' + tmppairs + "\n"
        conYML = conYML + 'totpairs: ' + str(len(tmpex.symbols)) + "\n"
        conYML = conYML + 'modefees: ' + str(tmpfeesmode) + "\n"
        conYML = conYML + yaml.dump(tmpex.urls) + "\n"
        conYML = conYML + yaml.dump(abilities) + "\n"
        conYML = conYML + yaml.dump(tmpfees) + "\n"
        # Remove empty lines
        conYML = os.linesep.join([s for s in conYML.splitlines() if s])
        # Save to YAML file
        self.writeCfgFile('conn', ex, conYML)

    def createCryptoInfo(self, ex):
        ex_class = getattr(ccxt, ex)
        tmpex = ex_class()
        # Map out variables
        tmpwww = tmpex.urls['www']
        tmpnom = tmpex.name
        tmpcert = str(tmpex.certified)
        # Check for duplicate urls
        if type(tmpwww) is list:
            tmpwww = str(tmpex.urls['www'][0])
        tmpapi = tmpex.urls['api']
        # Check fees
        try:
            tmpfees = tmpex.urls['fees']
            if type(tmpfees) is list:
                tmpfees = str(tmpex.urls['fees'][0])
        except BaseException:
            tmpfees = 'N/A'
        # Check for tmpapi being a dick!
        if type(tmpapi) is dict:
            try:
                tmpapi = tmpex.urls['api']['public']
            except BaseException:
                tmpapi = 'N/A'
        # Check for multiple countries
        try:
            tmpco = ', '.join(tmpex.countries)
        except BaseException:
            tmpco = 'N/A'
        # Join time frames
        try:
            tmptf = ', '.join(tmpex.timeframes.keys())
        except BaseException:
            tmptf = 'N/A'
        tmpto = str(tmpex.timeout)
        tmprl = str(tmpex.rateLimit)
        tmpat = ""
        # Cycle through HAS array
        for key in tmpex.has:
            if tmpex.has[key] or tmpex.has[key] == 'emulated':
                tmpat = tmpat + key + ', '
        # Create passback HTML to Javascript from Select OnChange
        infostr = "<b>Name:</b> " + tmpnom + "<br><b>Country:</b> " + tmpco + "<br>"
        infostr = infostr + "<b>CCXT Certified:</b> " + tmpcert + "<br>"
        infostr = infostr + "<b>URL:</b> <a href='" + tmpwww + "'>" + tmpwww + "</a><br>"
        infostr = infostr + "<b>Fees:</b> <a href='" + tmpfees + "'>" + tmpfees + "</a><br>"
        infostr = infostr + "<b>API:</b> <a href='" + tmpapi + "'>" + tmpapi + "</a><br>"
        infostr = infostr + "<b>TimeFrames:</b> " + tmptf + "<br>"
        infostr = infostr + "<b>Timeout:</b> " + tmpto + "<br>"
        infostr = infostr + "<b>RateLimit:</b> " + tmprl + "<br>"
        infostr = infostr + "<b>Abilities:</b> " + tmpat + "<br>"
        return infostr

    def gitCryptoQuotes(self, con):
        # Get YAML connection configuration from file
        cfdata = self.readCfgFile('conn', con + '.yml')
        # Get quotes from file
        # print(cfdata)
        quotes = cfdata['quotes'].split(', ')
        # Create response in HTML
        quotesRESP = "<option value='NANANANA'>Select " + con + " quote</option>"
        for quote in quotes:
            quotesRESP = quotesRESP + "<option value='" + quote + "'>" + quote + "</option>"
        return quotesRESP

    def gitCryptoPairs(self, con, quote):
        # Get YAML connection configuration from file
        cfdata = self.readCfgFile('conn', con + '.yml')
        # Extract pairs from pairs setting
        pairs = cfdata['pairs'].split(', ')
        # Create response in HTML
        pairsRESP = "<option value='NANANANA'>Select " + quote + " Pairs</option>"
        for pair in pairs:
            part = pair.split('/')
            if part[1] == quote:
                pairsRESP = pairsRESP + "<option value='" + pair + "'>" + pair + "</option>"
        return pairsRESP

    def createCryptoData(self, con, quote, symb, start):
        # Start time to UnixTimestamp in UTC
        format = '%A %d %B %Y'
        d = datetime.datetime.strptime(start, format)  # 3.2+
        d = pytz.utc.localize(d)
        start = time.mktime(d.timetuple())
        start = int(start * 1000)
        # Create temp Exchange
        ex_class = getattr(ccxt, con)
        tmpex = ex_class()
        # Interogate OHLCV
        tmpfirst = ''
        tmpmaxbars = ''
        if tmpex.has['fetchOHLCV']:
            data = tmpex.fetch_ohlcv(symb, '1m')
            tmpfirst = data[0][0]
            tmpmaxbars = len(data)
        # Create Data ID
        fsymb = re.sub('/', '_', symb)
        id = con.lower() + '_' + fsymb
        dataYML = "id: " + id + "\n"
        # Create Database table class
        Base = declarative_base()

        class OHBASE(Base):
            __tablename__ = id
            date = Column('date', Integer, primary_key=True)
            open = Column('open', Float)
            high = Column('high', Float)
            low = Column('low', Float)
            close = Column('close', Float)
            volume = Column('volume', Float)
        # Table creation object
        table_creation_sql = str(CreateTable(OHBASE.__table__))
        table_creation_sql = table_creation_sql.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS')
        # Create SQL table
        self.db.session.execute(table_creation_sql)
        # Create Data YAML
        dataYML = dataYML + 'enabled: false' + "\n"
        dataYML = dataYML + 'aggro: true' + "\n"
        dataYML = dataYML + 'con: ' + con + "\n"
        dataYML = dataYML + 'symb: ' + symb + "\n"
        dataYML = dataYML + 'first: ' + str(tmpfirst) + "\n"
        dataYML = dataYML + 'start: ' + str(start) + "\n"
        dataYML = dataYML + 'end: 0' + "\n"
        dataYML = dataYML + 'head: 0' + "\n"
        dataYML = dataYML + 'tail: 0' + "\n"
        dataYML = dataYML + 'count: 0' + "\n"
        dataYML = dataYML + 'maxbars: ' + str(tmpmaxbars) + "\n"
        dataYML = os.linesep.join([s for s in dataYML.splitlines() if s])
        # Save to YAML file
        self.writeCfgFile('data', id, dataYML)

    # def gitRunners(self):
        # print("last modified: %s" % time.ctime(os.path.getmtime(file)))
        # print("created: %s" % time.ctime(os.path.getctime(file)))

    def createSample(self, data, fromdate, todate, timeframe, selection):
        monthInMS = 43800 * 60 * 1000
        if selection != 'custom':
            todate = time.time() * 1000
            if selection == '1M':
                fromdate = todate - monthInMS
            if selection == '3M':
                fromdate = todate - 3 * monthInMS
            if selection == '6M':
                fromdate = todate - 6 * monthInMS
            if selection == '1Y':
                fromdate = todate - 12 * monthInMS
            if selection == '2Y':
                fromdate = todate - 24 * monthInMS
            if selection == '5Y':
                fromdate = todate - 60 * monthInMS
        else:
            # From date in UnixTimestamp in UTC
            format = '%A %d %B %Y'
            d = datetime.datetime.strptime(fromdate, format)  # 3.2+
            d = pytz.utc.localize(d)
            fromdate = time.mktime(d.timetuple())
            fromdate = int(fromdate * 1000)
            # To Date in UnixTimestamp in UTC
            format = '%A %d %B %Y'
            d = datetime.datetime.strptime(todate, format)  # 3.2+
            d = pytz.utc.localize(d)
            todate = time.mktime(d.timetuple())
            todate = int(todate * 1000)
        selState = 'SELECT * FROM ' + data + ' WHERE date BETWEEN ' + str(fromdate) + ' AND ' + str(todate)
        # print(selState,file=sys.stderr)
        result = self.db.session.execute(selState).fetchall()
        # print(result,file=sys.stderr)
        createSampledf = pd.DataFrame(result, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        if createSampledf.shape[0] == 0:
            return
        # Setup Datetime and Index
        # createSampledf['date'].astype('datetime64[ms]')
        # TODO EXCLUDE forming Candle
        # Create DatetimeIndex
        createSampledf['date'] = pd.to_datetime(createSampledf['date'], unit='ms')
        createSampledf.set_index('date', inplace=True)
        # Break up OHLC
        open = createSampledf['open']
        high = createSampledf['high']
        low = createSampledf['low']
        close = createSampledf['close']
        vols = createSampledf['volume']
        # Resample prices and vols
        sopen = open.resample(timeframe).first()
        shigh = high.resample(timeframe).max()
        slow = low.resample(timeframe).min()
        sclose = close.resample(timeframe).last()
        svols = vols.resample(timeframe).sum()
        # Join the two together
        result = pd.concat([sopen, shigh, slow, sclose, svols], axis=1)
        result.reset_index(inplace=True)
        result['date'] = result['date'].astype(np.int64) / int(1e6)
        sname = str(data) + '_' + timeframe + '_' + str(int(result['date'].iloc[0])) + '_' + str(int(result['date'].iloc[-1]))
        result.to_feather(self.sampleDataPath + sname + '.feather')

    def createNugget(self, sample, indie, depen, nana):
        en = enrichments.Enrichment()
        df = pd.read_feather(self.sampleDataPath + sample + '.feather')
        # print(df,file=sys.stderr)
        richcfg = self.readCfgFile('enrich', indie + '.yml')
        riches = richcfg['riches'].split(', ')
        for rich in riches:
            df = en.addIndi(rich, df)
        df = en.addDepen(depen, df)
        df = en.doNaN(nana, df)
        nfile = sample + '_' + indie + '_' + depen + '.feather'
        df.to_feather(self.nuggetDataPath + nfile)
