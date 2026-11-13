"""Column names of the raw Kaggle "Customer Personality Analysis" file, grouped by meaning."""

ID = "ID"
TARGET = "Response"  # accepted the offer in the last campaign

SPEND_COLUMNS = {
    "wine": "MntWines",
    "fruit": "MntFruits",
    "meat": "MntMeatProducts",
    "fish": "MntFishProducts",
    "sweet": "MntSweetProducts",
    "gold": "MntGoldProds",
}

PURCHASE_CHANNELS = {
    "web": "NumWebPurchases",
    "catalog": "NumCatalogPurchases",
    "store": "NumStorePurchases",
}
DEALS = "NumDealsPurchases"
WEB_VISITS = "NumWebVisitsMonth"

PRIOR_CAMPAIGNS = ["AcceptedCmp1", "AcceptedCmp2", "AcceptedCmp3", "AcceptedCmp4", "AcceptedCmp5"]

DEMOGRAPHIC_COLUMNS = ["Year_Birth", "Education", "Marital_Status", "Income", "Kidhome", "Teenhome"]
OTHER_COLUMNS = ["Dt_Customer", "Recency", "Complain"]

# Constant columns that hold the campaign economics: cost per contact and revenue per response.
COST_CONTACT = "Z_CostContact"
REVENUE = "Z_Revenue"

REQUIRED_COLUMNS = [
    ID,
    *DEMOGRAPHIC_COLUMNS,
    *OTHER_COLUMNS,
    *SPEND_COLUMNS.values(),
    *PURCHASE_CHANNELS.values(),
    DEALS,
    WEB_VISITS,
    *PRIOR_CAMPAIGNS,
    COST_CONTACT,
    REVENUE,
    TARGET,
]

DATE_FORMAT = "%d-%m-%Y"
