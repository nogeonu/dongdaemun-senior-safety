import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import box, Point
import matplotlib.pyplot as plt
import folium
import rasterio
from branca.colormap import LinearColormap
import branca.colormap as cm
from pyproj import Transformer
import os

# 환경변수 파일 경로 설정
env_dir = "환경변수"

# 중심 좌표 설정 (동대문구 중심)
center_lat = 37.5744
center_lon = 127.0395

# folium 지도 생성
m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

# 동대문구 경계 추가 (dongdaemun GeoDataFrame이 있다고 가정)
if 'dongdaemun' in locals():
    folium.GeoJson(
        dongdaemun.to_json(),
        name="동대문구",
        style_function=lambda x: {
            'fillColor': 'none',
            'color': 'blue',
            'weight': 3,
            'fillOpacity': 0
        }
    ).add_to(m)

# 격자별 시설 개수를 저장할 딕셔너리
facility_counts = {}

# 먼저 모든 asc 파일을 읽어서 시설 개수 데이터 수집
for filename in os.listdir(env_dir):
    if filename.endswith('.asc'):
        facility_name = filename.replace('.asc', '')
        file_path = os.path.join(env_dir, filename)
        
        with rasterio.open(file_path) as src:
            data = src.read(1)  # 첫 번째 밴드 읽기
            if facility_name not in facility_counts:
                facility_counts[facility_name] = data

# 시장 밀집도의 최대값과 최소값 계산 (의미있는 값들 중에서)
market_data = facility_counts.get('market_kde_density_log_weighted', None)
if market_data is not None:
    # 0이 아닌 값들의 통계 출력
    nonzero_values = market_data[market_data > 0]
    print("\n시장 밀집도 통계:")
    print(f"최대값: {np.max(market_data):.2e}")
    print(f"최소값 (0 제외): {np.min(nonzero_values):.2e}")
    print(f"평균값 (0 제외): {np.mean(nonzero_values):.2e}")
    print(f"중앙값 (0 제외): {np.median(nonzero_values):.2e}")
    
    # 상위 10개 값 출력
    top_10_values = sorted(nonzero_values, reverse=True)[:10]
    print("\n가장 높은 밀집도 10개:")
    for i, value in enumerate(top_10_values, 1):
        print(f"{i}위: {value:.2e}")
    
    # 데이터의 95퍼센타일 값을 찾아서 임계값으로 사용
    threshold = np.percentile(market_data[market_data > 0], 5)
    
    # 임계값보다 작은 값들은 0으로 설정
    market_data = np.where(market_data > threshold, market_data, 0)
    
    # 0이 아닌 값들에 대해서만 정규화 진행
    market_nonzero = market_data[market_data > 0]
    if len(market_nonzero) > 0:
        market_min = np.min(market_nonzero)
        market_max = np.max(market_nonzero)
        # 0-100 스케일로 정규화
        market_data = np.where(market_data > 0, 
                             (market_data - market_min) / (market_max - market_min) * 100, 
                             0)
        facility_counts['market_kde_density_log_weighted'] = market_data

# 위험도 평가 격자 추가 (accident_gdf가 있다고 가정)
if 'accident_gdf' in locals():
    for idx, row in accident_gdf.iterrows():
        # 현재 격자의 인덱스 계산
        grid_x = idx % 20  # 20x20 격자 기준
        grid_y = idx // 20
        
        # 위험도에 따른 색상 설정
        color = cm.linear.OrRd_09.scale(accident_gdf['value'].min(), 
                                      accident_gdf['value'].max())(row['value'])
        
        # 팝업 내용 생성
        popup_html = f"""
        <div style="font-family: 'Malgun Gothic', sans-serif;">
            <h4>격자 정보</h4>
            <p><b>위험도:</b> {row['value']:.2f}</p>
            <hr>
            <h5>시설 현황:</h5>
            <ul>
        """
        
        # 시설 이름 한글 매핑
        facility_korean = {
            'bus_stop': '버스정류장',
            'cctv_car': 'CCTV(차량)',
            'cctv_way_density': 'CCTV(보행)',
            'walklight': '보행자신호등',
            'crosswalk': '횡단보도',
            'streetlight': '가로등',
            'senior_facility': '노인시설',
            'intersection_threeway': '삼거리',
            'intersection_fourway': '사거리',
            'intersection_single': '단일로',
            'silverzone': '실버존',
            'led_density': 'LED',
            'car_out_density': '차량진출입구',
            'hospital_log': '병원',
            'market_kde_density_log_weighted': '시장 밀집도'
        }
        
        # 각 시설별 개수 추가 (0개인 것도 포함)
        for facility_name, counts in facility_counts.items():
            count = counts[grid_y, grid_x]
            korean_name = facility_korean.get(facility_name, facility_name)
            
            # 시장 KDE 밀도는 별도 처리
            if facility_name == 'market_kde_density_log_weighted':
                if count > 0:
                    popup_html += f"<li>{korean_name}: {count:.1f}%</li>"
                else:
                    popup_html += f"<li>{korean_name}: 없음</li>"
            else:
                popup_html += f"<li>{korean_name}: {int(count)}개</li>"
        
        popup_html += """
            </ul>
        </div>
        """
        
        # 격자 추가
        folium.GeoJson(
            row.geometry.__geo_interface__,
            name=f"위험도 격자 {row['value']:.2f}",
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.5
            },
            tooltip=f"위험도: {row['value']:.2f}",
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    # 위험도 범례 추가
    colormap = cm.linear.OrRd_09.scale(accident_gdf['value'].min(), 
                                     accident_gdf['value'].max())
    colormap.caption = '위험도 지수'
    colormap.add_to(m)

# 레이어 컨트롤 추가
folium.LayerControl().add_to(m)

# 지도 표시
m 