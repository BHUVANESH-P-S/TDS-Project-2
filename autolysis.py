import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import openai
from pathlib import Path
from google.colab import files
import requests
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
import networkx as nx
import geopandas as gpd

# Initialize OpenAI

def initialize_openai():
    from google.colab import userdata
    api_key = userdata.get('API_KEY')
    openai.api_key = api_key
    if not openai.api_key:
        raise EnvironmentError("API_KEY environment variable not set.")

# Load dataset
def load_dataset(file_path):
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        return df
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='latin1')
        return df
    except Exception as e:
        raise FileNotFoundError(f"Error loading file {file_path}: {e}")

# Perform basic analysis
def basic_analysis(df):
    summary = df.describe(include='all')
    missing_values = df.isnull().sum()
    column_types = df.dtypes
    df_info = df.info()

    insights = {
        "Summary": summary,
        "Missing_values": missing_values,
        "Column_types": column_types,
        "Dataset_info":df_info
    }

    return insights

# Outlier and anomaly detection
def detect_outliers(df):
    numerical_df = df.select_dtypes(include='number')
    if not numerical_df.empty:
        # Fill missing values with the mean of each column
        numerical_df = numerical_df.fillna(numerical_df.mean())
        
        # Apply Isolation Forest
        iso = IsolationForest(contamination=0.05, random_state=42)
        outliers = iso.fit_predict(numerical_df)
        df['Anomaly'] = outliers
    return df


# Correlation, regression, and feature importance analysis
def correlation_and_regression_analysis(df):
    numerical_df = df.select_dtypes(include='number')
    correlations = numerical_df.corr()
    if 'target' in df.columns:
        X = numerical_df.drop(columns=['target'])
        y = df['target']
        model = LinearRegression()
        model.fit(X, y)
        feature_importance = pd.Series(model.coef_, index=X.columns).sort_values(ascending=False)
        return correlations, feature_importance
    return correlations, None

# Time series analysis
def time_series_analysis(df):
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        time_series = df.set_index('date').select_dtypes(include='number').resample('M').mean()
        return time_series
    return None

# Geographic analysis
def geographic_analysis(df):
    if {'latitude', 'longitude'}.issubset(df.columns):
        geo_df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude))
        return geo_df
    return None

# Network analysis
def network_analysis(df):
    if {'source', 'target'}.issubset(df.columns):
        G = nx.from_pandas_edgelist(df, source='source', target='target')
        centrality = nx.degree_centrality(G)
        return centrality
    return None

# Generate visualizations
def generate_visualizations(df):
    charts = []

    # Correlation heatmap for numerical columns
    numerical_df = df.select_dtypes(include='number')
    if not numerical_df.empty:
        plt.figure(figsize=(10, 8))
        corr = numerical_df.corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f')
        heatmap_path = "correlation_heatmap.png"
        plt.savefig(heatmap_path)
        plt.close()
        charts.append(heatmap_path)

    # Histogram for numerical columns
    for col in numerical_df.columns:
        plt.figure()
        sns.histplot(df[col].dropna(), kde=True, bins=30)
        hist_path = f"histogram_{col}.png"
        plt.savefig(hist_path)
        plt.close()
        charts.append(hist_path)

    return charts

# Generate narrative using LLM
def generate_narrative(insights, images):
    prompt = f"""
    Dataset Analysis Report:
    Dataset Summary: {insights['Summary']}
    Missing Values: {insights['Missing_values']}
    Column Types: {insights['Column_types']}
    Dataset Info: {insights['Dataset_info']}

    Please provide a detailed narrative of the dataset, covering the following points:

    1. Dataset Overview
    2. Outliers and Anomalies
    3. Correlation, Regression, and Feature Importance
    4. Time Series Patterns
    5. Cluster Analysis Findings
    6. Geographic Insights
    7. Network Analysis Observations
    """

    response = requests.post(
        "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {openai.api_key}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": prompt}
            ]
        }
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

# Write results to README.md
def write_readme(narrative, charts):
    readme_path = "README.md"
    with open(readme_path, "w") as f:
        f.write("# Automated Data Analysis\n\n")
        if narrative:
            f.write(narrative + "\n\n")
        for chart in charts:
            f.write(f"![Chart]({chart})\n")

# Main function
def main():
    initialize_openai()
    file_path = Path('happiness.csv')
    df = load_dataset(file_path)

    # Perform analysis
    df = detect_outliers(df)
    correlations, feature_importance = correlation_and_regression_analysis(df)
    time_series = time_series_analysis(df)
    geo_df = geographic_analysis(df)
    centrality = network_analysis(df)

    insights = basic_analysis(df)
    charts = generate_visualizations(df)
    narrative = generate_narrative(insights, charts)

    # Write results
    write_readme(narrative, charts)
    print("Analysis complete. Results saved")

if __name__ == "__main__":
    main()
