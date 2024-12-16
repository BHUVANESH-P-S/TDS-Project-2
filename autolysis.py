import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import openai
from pathlib import Path
import requests
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
import geopandas as gpd
from PIL import Image

# Initialize OpenAI

def initialize_openai():
    openai.api_key = os.getenv('AIPROXY_TOKEN')
    if not openai.api_key:
        raise EnvironmentError("AIPROXY_TOKEN environment variable not set.")

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
    df_info=df.info()

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
        numerical_df = numerical_df.fillna(numerical_df.mean())
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

# Cluster analysis
def cluster_analysis(df):
    numerical_df = df.select_dtypes(include='number')
    if not numerical_df.empty:
        numerical_df = numerical_df.fillna(numerical_df.mean())
        kmeans = KMeans(n_clusters=3, random_state=0)
        df['Cluster'] = kmeans.fit_predict(numerical_df)
    return df

# Geographic analysis
def geographic_analysis(df):
    if {'latitude', 'longitude'}.issubset(df.columns):
        geo_df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude))
        return geo_df
    return None

# Generate visualizations
def generate_visualizations(df,output_dir):
    charts = []

    # Correlation heatmap for numerical columns
    numerical_df = df.select_dtypes(include='number')
    if not numerical_df.empty:
        plt.figure(figsize=(10, 8))
        corr = numerical_df.corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f')
        heatmap_path = output_dir/"correlation_heatmap.png"
        plt.savefig(heatmap_path)
        plt.close()
        charts.append(heatmap_path)

    # Histogram for numerical columns
    for col in numerical_df.columns:
        plt.figure()
        sns.histplot(df[col].dropna(), kde=True, bins=30)
        hist_path = output_dir/f"histogram_{col}.png"
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
    Dataset Information: {insights['Dataset_info']}

    Please provide a detailed narrative of the dataset, covering the following points:

    1. Dataset Overview
    2. Outliers and Anomalies
    3. Correlation, Regression, and Feature Importance
    4. Time Series Patterns
    5. Cluster Analysis Findings
    6. Geographic Insights
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
def write_readme(output_dir,narrative, charts):
    readme_path = output_dir/"README.md"
    with open(readme_path, "w") as f:
        f.write("# Automated Data Analysis\n\n")
        if narrative:
            f.write(narrative + "\n\n")
        for chart in charts:
            f.write(f"![Chart]({chart})\n")

# Main function
def main(file_path):
    initialize_openai()
    df = load_dataset(file_path)

# Prepare output directory
    dataset_name = Path(file_path).stem  # Get the file name without extension
    output_dir = Path("output") / dataset_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Perform analysis
    df = detect_outliers(df)
    correlations, feature_importance = correlation_and_regression_analysis(df)
    time_series = time_series_analysis(df)
    df = cluster_analysis(df)
    geo_df = geographic_analysis(df)

    insights = basic_analysis(df)
    charts = generate_visualizations(df,output_dir)
    narrative = generate_narrative(insights, charts)

    # Write results
    write_readme(output_dir,narrative, charts)
    print("Analysis complete. Results saved")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py dataset.csv")
    else:
        file_path= sys.argv[-1]
        main(file_path)
