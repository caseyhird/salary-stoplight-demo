import streamlit as st
from pydantic import BaseModel
from enum import Enum
from typing import Optional
import pandas as pd

# 1) Sample in-memory statistics by specialty and percentiles.
#    For real use, replace with your actual data or fetch from a database.
class Specialty(Enum):
    SURGERY_TRAUMA = "Surgery: Trauma"

class Metric(Enum):
    TOTAL_COMPENSATION = "Total Compensation"
    TOTAL_HOURS = "Total Hours"
    TOTAL_RVUS = "Total RVUs"
    COMPERSATION_PER_HOUR = "Compensation per Hour"
    COMPERSATION_PER_RVU = "Compensation per RVU"

class TableRow(BaseModel):
    specialty: Specialty
    practice_type: str
    metric: Metric
    groups: Optional[int] = None
    providers: Optional[int] = None
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    p90: Optional[float] = None

STATS_TABLE: list[TableRow] = [
    TableRow(
        specialty=Specialty.SURGERY_TRAUMA,
        practice_type="All",
        metric=Metric.TOTAL_COMPENSATION,
        groups=76,
        providers=262,
        mean=485989,
        std_dev=160927,
        p25=405815,
        p50=473355,
        p75=550500,
        p90=662930,
    ),
    TableRow(
        specialty=Specialty.SURGERY_TRAUMA,
        practice_type="All",
        metric=Metric.TOTAL_RVUS,
        providers=55,
        p25=6270,
        p50=11107,
        p75=14285,
    ),
    TableRow(
        specialty=Specialty.SURGERY_TRAUMA,
        practice_type="All",
        metric=Metric.COMPERSATION_PER_RVU,
        providers=47,
        p25=34.78,
        p50=47.45,
        p75=64.67,
    ),
]

class PaymentTemplate(Enum):
    BY_RVUS = "By RVUs"
    HOURLY = "Hourly"

class TemplateForm():
    def __init__(self, template: PaymentTemplate):
        self.template = template
        
    def compute_metric(self, metric: Metric):
        pass

class HourlyTemplateForm(TemplateForm):
    def __init__(self, template: PaymentTemplate):
        super().__init__(template)
        
        # Hourly-based inputs
        self.onsite_rate = st.number_input("Dollars per hour (On-site)", min_value=0.0, value=200.0)
        self.call_rate = st.number_input("Dollars per hour (Unrestricted On-call)", min_value=0.0, value=50.0)
        self.other_compensation = st.number_input("Other Compensation", min_value=0.0, value=0.0)
        
        # 4) Sliders for productivity (# of hours)
        st.subheader("Productivity Inputs")
        self.onsite_hours = st.slider("On-site hours per year", min_value=0, max_value=4000, value=2080)
        self.call_hours = st.slider("On-call hours per year", min_value=0, max_value=4000, value=500)
        
    def compute_metric(self, metric: Metric):
        if metric == Metric.TOTAL_COMPENSATION:
            return self._compute_compensation()
        elif metric == Metric.TOTAL_HOURS:
            return self._compute_total_hours()
        elif metric == Metric.COMPERSATION_PER_HOUR:
            return self._compute_compensation() / self._compute_total_hours()
        else:
            return None

    def _compute_compensation(self):
        return self.onsite_rate * self.onsite_hours + self.call_rate * self.call_hours + self.other_compensation
    
    def _compute_total_hours(self):
        return self.onsite_hours + self.call_hours

class RVUTemplateForm(TemplateForm):
    def __init__(self, template: PaymentTemplate):
        super().__init__(template)
        
        # RVU-based inputs
        self.base_comp = st.number_input("Base Compensation", min_value=0.0, value=300000.0)
        self.rvu_threshold = st.number_input("Threshold RVUs", min_value=0, value=5000)
        self.rvu_rate = st.number_input("Compensation Rate Above Threshold (per RVU)", min_value=0.0, value=50.0)
        self.other_compensation = st.number_input("Other Compensation", min_value=0.0, value=0.0)
        
        # 4) Slider for # of RVUs
        st.subheader("Productivity Inputs")
        self.total_rvus = st.slider("Total RVUs", min_value=0, max_value=20000, value=7000)
        
    def compute_metric(self, metric: Metric):
        if metric == Metric.TOTAL_COMPENSATION:
            return self._compute_compensation()
        elif metric == Metric.TOTAL_RVUS:
            return self._compute_total_rvus()
        elif metric == Metric.COMPERSATION_PER_RVU:
            return self._compute_compensation() / self._compute_total_rvus()
        else:
            return None
        
    def _compute_compensation(self):
        if self.total_rvus <= self.rvu_threshold:
            total_rvus_compensation = self.base_comp
        else:
            additional_rvus = self.total_rvus - self.rvu_threshold
            total_rvus_compensation = self.base_comp + additional_rvus * self.rvu_rate
        
        return total_rvus_compensation + self.other_compensation
    
    def _compute_total_rvus(self):
        return self.total_rvus

def get_percentile_for_comp(stats, comp):
    """
    Given the specialty and total compensation, 
    return the approximate percentile.
    """
    if stats.p25 is not None and comp < stats.p25:
        return "below 25th percentile", "orange"
    elif stats.p50 is not None and comp < stats.p50:
        return "between 25th and 50th percentile", "green"
    elif stats.p75 is not None and comp < stats.p75:
        return "between 50th and 75th percentile", "yellow"
    elif stats.p90 is not None and comp < stats.p90:
        return "between 75th and 90th percentile", "red"
    else:
        return "above 90th percentile", "red"

def main():
    st.title("[DEMO] Physician Compensation Stoplight")

    # 1) Select template and specialty
    template = st.selectbox("Select Payment Template", [template.value for template in PaymentTemplate])
    specialty = st.selectbox("Select Specialty", [row.specialty.value for row in STATS_TABLE])
    
    # 2) Depending on the selected template, show relevant inputs
    st.subheader("Proposed Compensation Inputs")
    if template == PaymentTemplate.HOURLY.value:
        template_form = HourlyTemplateForm(template)
    else:  # template == PaymentTemplate.BY_RVUS.value
        template_form = RVUTemplateForm(template)
    
    rows = [row for row in STATS_TABLE if row.specialty.value == specialty]
    for row in rows:
        metric = template_form.compute_metric(row.metric)
        if metric is None:
            continue
        
        # 3) Display summary statistics for the selected specialty
        st.subheader(f"{row.metric.value}")
        row_data = row.model_dump()
        row_data = {k: v for k, v in row_data.items() if v is not None}
        row_data["specialty"] = row.specialty.value
        row_data["metric"] = row.metric.value
        df = pd.DataFrame([row_data])
        st.dataframe(df, use_container_width=True)
        
        # Display the percentile range
        percentile_str, color = get_percentile_for_comp(row, metric)
        st.markdown(
            f"The proposed {row.metric.value}, {metric:,.2f}, is in the <span style='color:{color}'>{percentile_str}</span> for {specialty}.",
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
