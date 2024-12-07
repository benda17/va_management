import pandas as pd
import streamlit as st
from consts import *

# Function to read Google Sheets
def read_google_sheet(sheet_id: str, sheet_tab_gid: int = 0) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={sheet_tab_gid}"
    return pd.read_csv(url)

# Function to calculate total hours
def calculate_total_hours(df: pd.DataFrame, from_date) -> float:
    columns_of_duration = list(
        set(DURATION_COLUMN_NAMES).intersection(set([col.capitalize() for col in df.columns.tolist()])))
    df = filter_dates(df, from_date)
    if pd.api.types.is_string_dtype(df[columns_of_duration]):
        df[columns_of_duration] = df[columns_of_duration[0]].str.extract('(\d+)').astype(int)
    return float(df[columns_of_duration].astype(float).sum())

# Function to filter dates
def filter_dates(df: pd.DataFrame, from_date) -> pd.DataFrame:
    date_column = list(
        set(DATE_COLUMN_NAMES).intersection(set([col.capitalize() for col in df.columns.tolist()])))[0]
    df = format_dates(df, date_column)
    from_date = pd.to_datetime(from_date, format="%d/%m/%Y")
    return df[df[date_column] >= from_date]

# Function to format dates
def format_dates(df, date_column) -> pd.DataFrame:
    for format_ in DATE_FORMATS:
        try:
            df[date_column] = pd.to_datetime(df[date_column], format=format_)
            return df
        except ValueError:
            continue
    df[date_column] = pd.to_datetime(df[date_column], infer_datetime_format=True, dayfirst=True)
    return df

# Function to format the initial DataFrame
def format_initial_df(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [col.strip().capitalize() for col in df.columns.tolist()]
    needed_columns = list(set(df.columns).intersection(set(DURATION_COLUMN_NAMES + DATE_COLUMN_NAMES)))
    df = df[needed_columns]
    df = df.dropna()
    df = df.reset_index(drop=True)
    return df

# Function to generate a client-specific message
def generate_client_message(first_name, last_name, paid_hours, used_hours):
    overdue_hours = used_hours - paid_hours if used_hours > paid_hours else 0
    overdue_text = f"בנוסף, נוצר חוב של {overdue_hours} שעות." if overdue_hours > 0 else ""
    payment_text = f"יש להסדיר תשלום על {overdue_hours} שעות." if overdue_hours > 0 else "יש להסדיר תשלום על חבילה חדשה."

    return f"""
ניהול החנויות של בנדה בע"מ

היי {first_name} {last_name}!

חבילת השעות שלך לניהול החנויות בחברת בנדה בע"מ הסתיימה.
{overdue_text}

בפועל שילמת על {paid_hours} שעות, וכעת עברו {used_hours} שעות.

גם בקבוצת הWhatsapp שלנו עם העובד שלך, גם בגיליון הניהול של החנות שלך, וגם באתר ניהול החנויות שלנו, מוצגים לך הביצועים של החנות.

במידה ואנחנו ממשיכים, {payment_text}

אם עולות ספקות / דברים שמפריעים, רואי מבקש להעלות את זה מולו במיידי! אנחנו רוצים שיהיה לך שירות הכי טוב שאפשר.

תודה!

צוות ניהול החנויות של רואי בנדה.
"""

# Streamlit App
def main():
    st.title("ניטור חבילת שעות - בנדה בעמ")
    st.write("לחצו על הכפתור כדי להתחיל את תהליך מדידת השעות")

    if st.button("ייצא מידע והודעות"):
        try:
            # Fetch main Google Sheet
            clients_info = read_google_sheet(SHEETS_INFO_TABLE_KEY, SHEETS_INFO_TABLE_GID)

            # Process each client's data
            hours_since_last_payment = []
            for client in range(len(clients_info)):
                try:
                    client_df = read_google_sheet(
                        clients_info.iloc[client][SHEET_ID_COLUMN],
                        clients_info.iloc[client][GID_COLUMN]
                    )
                    client_df = format_initial_df(client_df)
                    hours_since_last_payment.append(
                        calculate_total_hours(client_df, clients_info.iloc[client][PURCHASE_DATE_COLUMN])
                    )
                except Exception as e:
                    hours_since_last_payment.append(999)  # Default value on error
                    continue
            
            # Add processed data to the main DataFrame
            clients_info[HOURS_SINCE_PAYMENT] = hours_since_last_payment
            clients_info[HOURS_PERCENT] = clients_info[HOURS_SINCE_PAYMENT] / clients_info[LIMIT_COLUMN]

            # Filter clients who have used all or exceeded their purchased hours
            overdue_clients = clients_info[clients_info[HOURS_SINCE_PAYMENT] >= clients_info[LIMIT_COLUMN]]

            # Generate and display messages for overdue clients only
            for i, client in overdue_clients.iterrows():
                first_name = client[FIRST_NAME_COLUMN]
                last_name = client[LAST_NAME_COLUMN]
                paid_hours = client[LIMIT_COLUMN]
                used_hours = client[HOURS_SINCE_PAYMENT]

                message = generate_client_message(first_name, last_name, paid_hours, used_hours)
                st.text_area(f"Message for {first_name} {last_name}", message, height=250)

            if overdue_clients.empty:
                st.info("No clients have used up their hours.")

        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
