from dbm.DBmssql import MSSQL
from cfgr.idpw import get_token

import xlwings as xw
import pandas as pd
import numpy as np

from datetime import date, datetime, timedelta


def get_price_from_sql(from_:date,
                           to_:date,
                           idxs: list,
                           type:str = "o",
                           flds: str = 'PX_Last',
                           ffill:bool = True) -> pd.DataFrame:

    server = MSSQL.instance()
    server.login(
        id=get_token('id'),
        pw=get_token('pw')
    )

    # 시작일이 공휴일이면 ffill 할 수가 없어 넉넉하게 과거 10일 데이터 불러와서 출력은 시작일부터
    # DB에 2000/01/04 부터 들어가 있어 CSI300은 처음엔 NaN으로 나옴
    if from_ < date(2000, 1, 4):
        from_ = date(2000, 1, 4)

    from_ = from_ - timedelta(10)

    # query 조건
    cond_name = [f"NAME = '{idx}'" for idx in idxs]
    cond_name = " or ".join(cond_name)

    cond = [
        f"DATE >= '{from_.strftime('%Y%m%d')}'",
        f"DATE <= '{to_.strftime('%Y%m%d')}'",
        f"({cond_name})",
        f"TYPE = '{flds}'"
    ]

    cond = ' and '.join(cond)

    # data 불러오기
    col = ['DATE', 'NAME', 'TICKER', 'TYPE', 'VALUE']
    d = server.select_db(
        database='WSOL',
        schema='drv',
        table='price',
        column=col,
        condition=cond
    )

    # data 가공
    d = pd.DataFrame(d)
    d = pd.pivot_table(d, values=d.columns[4], index=d.columns[0], columns=d.columns[1])
    d.index = pd.Series([datetime.strptime(day, "%Y%m%d") for day in d.index])

    # DB에서 받아온 index는 datetime 형태, date만 있는 object 타입으로 바꿔줌(class_els와의 호환 위해)
    d.index = d.index.date

    # type = 'w'인 경우도 db에 있는 날까지 나오도록
    to_ = d.index[-1]

    d.index.name = "Date"

    # 공휴일, 휴일제외 original version
    if type == "o":
        if ffill is True:
            d.fillna(method='ffill', inplace=True)
            return d.iloc[10:, :]
        else:
            return d.iloc[10:, :]

    # 모든 날 추가한 version
    elif type == "w":
        dt_rng = pd.date_range(from_, to_).date
        d_weekend = pd.DataFrame(index=dt_rng, columns=idxs)
        d_weekend.index.name = "Date"

        for day in d_weekend.index:
            try:
                d_weekend.loc[day] = d.loc[day]

            except KeyError as e:
                d_weekend.loc[day] = [np.nan] * len(idxs)

        if ffill is True:
            d_weekend.fillna(method='ffill', inplace=True)

            return d_weekend.iloc[10:, :]
        else:
            return d_weekend.iloc[10:, :]


if __name__ =="__main__":
    start = date(2012, 7, 14)
    end = date.today()
    underlying = ['KOSPI200', "EUROSTOXX50", "S&P500"]
    df = get_price_from_sql(start, end, underlying, type="w")

    xw.view(df)

