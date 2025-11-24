import streamlit as st
import pandas as pd
import altair as alt

@st.cache_data
def load_data(data: str) -> pd.DataFrame:
    # Cache our mission data
    df = pd.read_csv(data)

    #Convert Dates to datetime64 type
    df['Date'] = pd.to_datetime(df.Date)

    #Frequency counter for companies
    company_freq = df['Company'].value_counts()

    return df, company_freq

class SpaceMissions:

    def __init__(self, df, company_freq):
        self.df = df
        self.company_freq = company_freq
        #Convert Dates to datetime64 type
        self.df['Date'] = pd.to_datetime(self.df.Date)

    def getTopCompaniesByMissionCount(self, n: int) -> list:
        '''Returns the top N companies ranked by total number of missions.'''
        nLargest = self.company_freq.nlargest(n)
        return list(zip(nLargest.index, [int(x) for x in nLargest.values]))

    def getMissionCountByCompany(self, companyName: str) -> int:
        '''Returns total number of missions given name'''
        if companyName in self.company_freq:
            return self.company_freq[companyName]
        else:
            return 0
        
    def getSuccessRate(self, companyName: str) -> float:
        '''Calculates the success rate for a given company as a percentage. (Rounded to 2 decimal places)'''
        totalMissions = self.df[self.df['Company']==companyName]
        #Safeguard divide by 0 error
        if len(totalMissions) == 0:
            return 0.0
        else:
            successMissions = totalMissions[totalMissions['MissionStatus']=='Success']
            rate = round(len(successMissions)/len(totalMissions),2)
            return rate

    def getMissionsByDateRange(self, startDate: str, endDate: str) -> list:
        '''Returns a list of all mission names launched between startDate and endDate (inclusive)'''
        try:
            startDateObject = pd.to_datetime(startDate)
            endDateObject = pd.to_datetime(endDate)
            return self.df.loc[(self.df['Date']>=startDateObject) & (self.df['Date']<=endDateObject)]['Mission'].to_list()
        except Exception as e:
            return []
        
    def getMissionStatusCount(self) -> dict:
        '''Returns the count of missions for each mission status.'''
        failed = len(self.df[self.df['MissionStatus']=='Failure'])
        success = len(self.df[self.df['MissionStatus']=='Success'])
        partialFailure = len(self.df[self.df['MissionStatus']=='Partial Failure'])
        preLaunchFailure = len(self.df[self.df['MissionStatus']=='Prelaunch Failure'])
        return {
            'Successful':success,
            "Failed":failed,
            "Partial Faliure":partialFailure,
            "Prelaunch Failure":preLaunchFailure
        }
    
    def getMissionsByYear(self, year: int) -> int:
        '''Return total number of missions launched in a specific year'''
        return len(self.df[self.df['Date'].dt.year==year])
         
    def getMostUsedRocket(self) -> str:
        '''Return the name of the most used rocket'''
        rocketsFrequency = self.df['Rocket'].value_counts()
        mostUsedRocket = rocketsFrequency.nlargest(1)
        return mostUsedRocket.index[0]

    def getAverageMissionsPerYear(self,startYear: int, endYear: int) -> float:
        '''Calculates the average number of missions per year over a given range.'''
        #avoid negative or 0 denominator
        if startYear>endYear:
            return 0.0
        yearCounts = self.df.loc[
            (self.df['Date'].dt.year>=startYear) & (self.df['Date'].dt.year<=endYear)
        ].groupby(self.df['Date'].dt.year).size()
        print(yearCounts)
        return round(yearCounts.sum()/(endYear-startYear+1),2)
    

class SpaceMissionsVizualizer:
    def __init__(self, df, company_freq):
        st.title('Space Mission Visualizer - Brian Fedelin')
        self.sm = SpaceMissions(df, company_freq)
    
    def showDF(self, df):
        st.dataframe(df)

    def missionStatusAltairChart(self, status: dict) -> None:
        status_df = pd.DataFrame({
            "Status": list(status.keys()),
            "Count": list(status.values()),
        })

        chart = (
            alt.Chart(status_df)
            .mark_arc()
            .encode(
                theta="Count:Q",
                color="Status:N",
                tooltip=["Status", "Count"],
            )
        )

        st.subheader("Mission Status Breakdown")
        st.altair_chart(chart, use_container_width=True)

    def topCompaniesBarChart(self, top_companies: list[tuple]) -> None:
        '''Display a bar chart of the top N companies by mission count.'''
        df = pd.DataFrame(top_companies, columns=["Company", "Missions"])
        df = df.set_index("Company") 

        st.bar_chart(df, use_container_width=True, sort='Missions')

    def companySuccessRateChart(self, top_companies: list[tuple]) -> None:
        companies = [company[0] for company in top_companies]
        success_rates = [self.sm.getSuccessRate(company) for company in companies]
        df = pd.DataFrame({'company':companies,
                           'rates':success_rates
                           })
        df = df.set_index('company')
        st.bar_chart(df, use_container_width=True, sort='rates')

    def missionsPerYearLineChart(self) -> None:
        """Display total missions per year as a line chart."""
        years = self.sm.df['Date'].dt.year
        start_year = int(years.min())
        end_year = int(years.max())

        year_list = list(range(start_year, end_year + 1))
        mission_counts = [self.sm.getMissionsByYear(y) for y in year_list]

        df_years = pd.DataFrame(
            {"Year": year_list, "Missions": mission_counts}
        ).set_index("Year")

        st.subheader("Missions Per Year")
        st.line_chart(df_years, use_container_width=True)
    
    def companyDetailsPanel(self) -> None:
        """Show total missions & success rate for a selected company."""
        st.subheader("Company Details")

        companies = sorted(self.sm.company_freq.index.tolist())
        company = st.selectbox("Select a company", companies)

        total = self.sm.getMissionCountByCompany(company)
        success_rate = self.sm.getSuccessRate(company) * 100  

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Missions", total)
        with col2:
            st.metric("Success Rate", f"{success_rate:.1f}%")

    def missionsByDateRangeExplorer(self) -> None:
        """Explore missions launched within a selected date range."""
        st.subheader("Missions by Date Range")

        min_date = self.sm.df["Date"].min().date()
        max_date = self.sm.df["Date"].max().date()

        date_input = st.date_input(
            "Select date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        if isinstance(date_input, (list, tuple)):
            if len(date_input) == 2:
                start_date, end_date = date_input
            elif len(date_input) == 1:
                start_date = end_date = date_input[0]
            else:
                return 
        else:
            start_date = end_date = date_input

        if start_date and end_date:
            missions = self.sm.getMissionsByDateRange(
                start_date.isoformat(), end_date.isoformat()
            )
            st.write(f"**{len(missions)}** missions found in this range.")
            if missions:
                st.dataframe(pd.DataFrame({"Mission": missions}))

    def mostUsedRocketHighlight(self) -> None:
        """Highlight the most used rocket."""
        st.subheader("Most Used Rocket")

        rocket = self.sm.getMostUsedRocket()
        count = len(self.sm.df[self.sm.df["Rocket"] == rocket])

        st.metric("Most Used Rocket", rocket)
        st.caption(f"Used in {count} missions.")

    def averageMissionsPerYearPanel(self) -> None:
        """Show average missions per year for a selected year range."""
        st.subheader("Average Missions per Year")

        years = self.sm.df["Date"].dt.year
        min_year, max_year = int(years.min()), int(years.max())

        start_year, end_year = st.slider(
            "Select year range",
            min_year,
            max_year,
            (min_year, max_year),
        )

        avg = self.sm.getAverageMissionsPerYear(start_year, end_year)
        st.metric(
            "Avg missions / year",
            f"{avg:.2f}",
            help=f"From {start_year} to {end_year}",
        )

    def createApp(self):
        n = st.number_input('insert number of top companies', value=3, step=1, min_value=0)

        col1, col2 = st.columns(2)
        with col1: 
            st.subheader(f'Mission count of top {n} companies (by mission count)')
            self.topCompaniesBarChart(self.sm.getTopCompaniesByMissionCount(n))
        with col2:
            st.subheader(f'Success rates of top {n} companies (by mission count)')
            self.companySuccessRateChart(self.sm.getTopCompaniesByMissionCount(n))
        
        self.missionsPerYearLineChart()
        self.companyDetailsPanel()
        self.missionsByDateRangeExplorer()
        self.mostUsedRocketHighlight()
        self.averageMissionsPerYearPanel()
        self.showDF(self.sm.df)


df, company_freq = load_data('./data/space_missions.csv')
        
def testFunctions():
    sm = SpaceMissions(df, company_freq)
    
    year = 1957
    company = 'CASC'
    n=3
    startYear = 2023
    endYear = 1957
    startDate = '1957-10-04'
    endDate = 'twentyfifteen'

    topCompanies = sm.getTopCompaniesByMissionCount(n)
    missionCount = sm.getMissionCountByCompany(company)
    topRocket = sm.getMostUsedRocket()
    yearFreq = sm.getMissionsByYear(year)
    avgMissionsPerYear = sm.getAverageMissionsPerYear(startYear, endYear)
    missionByDateRange = sm.getMissionsByDateRange(startDate, endDate)
    missionsByYear = sm.getMissionsByYear(year)
    missionStatusCount = sm.getMissionStatusCount()

    print(f'top companies: {topCompanies}')
    print(f'count for {company}: {missionCount}')
    print(f'most used rocket: {topRocket}')
    print(f'amount of missions in {year}: {yearFreq}')
    print(f'Missions by {year}: {missionsByYear} ')
    print(f'Missions by date range: {missionByDateRange}')
    print(f'missions per year from 1957-1958 {avgMissionsPerYear}')
    print(f'mission status count: {missionStatusCount}')

def app():
    smv = SpaceMissionsVizualizer(df, company_freq)
    smv.createApp()

app()

