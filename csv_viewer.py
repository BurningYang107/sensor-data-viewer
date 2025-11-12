#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器数据图表工具
作者：KeNaiXin开发团队
功能：读取CSV文件并展示DIF/RAW数据趋势
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="传感器数据可视化工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 标题和说明
st.title("📊 传感器数据图表工具")
st.markdown("---")
st.write("💡 支持从KeNaiXin APP导出的CSV文件，轻松分析DIF和RAW数据的变化趋势")

# 侧边栏配置
st.sidebar.header("🔧 控制面板")
st.sidebar.markdown("")

# 文件上传
st.sidebar.subheader("📤 文件上传")
uploaded_file = st.sidebar.file_uploader(
    "选择CSV文件",
    type=['csv'],
    help="点击选择从APP导出的CSV文件"
)

# 处理时间戳的辅助函数
def process_timestamp_column(df):
    """检测并处理时间戳列"""
    timestamp_columns = ['时间', '时间戳', 'timestamp', '时间（秒）', 'Time', 'time']

    # 查找时间戳列
    ts_col = None
    for col in df.columns:
        if col in timestamp_columns or '时间' in col or 'time' in col.lower() or 'timestamp' in col.lower():
            ts_col = col
            break

    if ts_col:
        try:
            # 转换为datetime类型
            df[ts_col] = pd.to_datetime(df[ts_col])
            return df, ts_col
        except Exception as e:
            st.warning(f"⚠️ 时间列转换失败: {str(e)}")
            return df, None
    return df, None

# 处理文件读取
if uploaded_file is not None:
    try:
        # 读取CSV
        df = pd.read_csv(uploaded_file)

        # 处理时间戳列
        df, timestamp_col = process_timestamp_column(df)

        # 数据概览
        st.subheader("📋 数据概览")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总数据量", len(df))

        if '是否入耳' in df.columns:
            col2.metric("入耳数据", len(df[df['是否入耳'] == '是']))
            col3.metric("出耳数据", len(df[df['是否入耳'] == '否']))
        else:
            col2.metric("入耳数据", "N/A")
            col3.metric("出耳数据", "N/A")

        if timestamp_col:
            time_range = f"{df[timestamp_col].min().strftime('%m-%d %H:%M')} ~ {df[timestamp_col].max().strftime('%m-%d %H:%M')}"
            col4.metric("时间范围", time_range)
        else:
            col4.metric("时间范围", "无时间列")

        # 检测数值异常（>1000%）
        abnormal_dif = 0
        abnormal_raw = 0

        if 'DIF百分比' in df.columns:
            dif_values = pd.to_numeric(df['DIF百分比'].astype(str).str.replace('%', ''), errors='coerce')
            abnormal_dif = (dif_values > 1000).sum()

        if 'RAW百分比' in df.columns:
            raw_values = pd.to_numeric(df['RAW百分比'].astype(str).str.replace('%', ''), errors='coerce')
            abnormal_raw = (raw_values > 1000).sum()

        total_abnormal = abnormal_dif + abnormal_raw

        if total_abnormal > 0:
            st.warning(f"⚠️ 检测到 {total_abnormal} 条数值异常数据（>1000%）")

        # 数据预览 - 支持点击展开完整数据
        with st.expander("🔍 查看原始数据", expanded=False):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.dataframe(df, use_container_width=True, height=300)

            with col2:
                st.write("")
                if st.button("📊 点击查看完整数据", use_container_width=True):
                    st.dataframe(df, use_container_width=True, height=None)

        st.markdown("---")

        # 数据筛选
        st.subheader("🔎 数据筛选")

        # 筛选器容器 - 调整为4列（添加时间戳筛选）
        filter_cols = st.columns(4)

        # 筛选入耳状态
        with filter_cols[0]:
            if '是否入耳' in df.columns:
                ear_status = st.multiselect(
                    "入耳状态",
                    options=df['是否入耳'].unique(),
                    default=df['是否入耳'].unique(),
                    help="选择要显示的入耳/出耳数据"
                )
                df_filtered = df[df['是否入耳'].isin(ear_status)]
            else:
                df_filtered = df.copy()

        # 筛选用户名
        with filter_cols[1]:
            if '用户名' in df_filtered.columns and not df_filtered['用户名'].isna().all():
                username_options = ['全部'] + [str(u) for u in df_filtered['用户名'].dropna().unique()]
                username = st.selectbox(
                    "选择用户",
                    options=username_options,
                    help="选择特定用户的数据"
                )
                if username != '全部':
                    df_filtered = df_filtered[df_filtered['用户名'].astype(str) == username]
            else:
                username = '全部'

        # 筛选左右耳
        with filter_cols[2]:
            if '左右耳' in df.columns:
                ear_side = st.multiselect(
                    "左右耳",
                    options=df['左右耳'].unique(),
                    default=df['左右耳'].unique(),
                    help="选择左耳或右耳数据"
                )
                df_filtered = df_filtered[df_filtered['左右耳'].isin(ear_side)]

        # 时间戳筛选
        with filter_cols[3]:
            if timestamp_col and len(df) > 0:
                st.markdown("**⏰ 时间范围**")
                try:
                    # 获取时间范围
                    min_time = df[timestamp_col].min()
                    max_time = df[timestamp_col].max()

                    # 创建两列来放置开始和结束时间选择器
                    time_col1, time_col2 = st.columns(2)

                    with time_col1:
                        st.markdown("**开始时间**")
                        start_date = st.date_input(
                            "开始日期",
                            value=min_time.date(),
                            min_value=min_time.date(),
                            max_value=max_time.date(),
                            key="start_date",
                            help="选择开始日期"
                        )
                        start_time = st.time_input(
                            "开始时间",
                            value=min_time.time(),
                            key="start_time",
                            help="选择开始时间"
                        )

                    with time_col2:
                        st.markdown("**结束时间**")
                        end_date = st.date_input(
                            "结束日期",
                            value=max_time.date(),
                            min_value=min_time.date(),
                            max_value=max_time.date(),
                            key="end_date",
                            help="选择结束日期"
                        )
                        end_time = st.time_input(
                            "结束时间",
                            value=max_time.time(),
                            key="end_time",
                            help="选择结束时间"
                        )

                    # 组合日期和时间
                    start_datetime = pd.Timestamp.combine(pd.to_datetime(start_date), start_time)

                    # 结束时间：如果是00秒，自动扩展到59.999秒
                    if end_time.second == 0 and end_time.microsecond == 0:
                        end_datetime = pd.Timestamp.combine(pd.to_datetime(end_date), end_time) + pd.Timedelta(seconds=59, microseconds=999999)
                    else:
                        end_datetime = pd.Timestamp.combine(pd.to_datetime(end_date), end_time)

                    # 应用时间筛选
                    df_filtered = df_filtered[
                        (df_filtered[timestamp_col] >= start_datetime) &
                        (df_filtered[timestamp_col] <= end_datetime)
                    ]

                    # 显示当前选择的时间范围
                    display_start = start_datetime.strftime('%Y-%m-%d %H:%M')
                    display_end = end_datetime.strftime('%Y-%m-%d %H:%M')
                    st.caption(f"📅 {display_start} ~ {display_end} (注：结束时间已自动包含该分钟内的所有秒数)")

                except Exception as e:
                    st.warning(f"⚠️ 时间筛选设置失败: {str(e)}")
            else:
                st.info("ℹ️ 无时间列" if not timestamp_col else "无数据")

        st.markdown("")
        st.write(f"✅ 筛选后数据量：{len(df_filtered)} 条")

        if len(df_filtered) == 0:
            st.error("❌ 筛选后没有数据，请调整筛选条件")
            st.stop()

        st.markdown("")

        # 图表展示前添加分页控制，让图表显示当前页数据
        st.subheader("📊 数据分页")

        # 先过滤掉数值异常（>1000%）
        df_filtered_clean = df_filtered.copy()

        if 'DIF百分比' in df_filtered_clean.columns:
            dif_values = pd.to_numeric(df_filtered_clean['DIF百分比'].astype(str).str.replace('%', ''), errors='coerce')
            df_filtered_clean = df_filtered_clean[dif_values <= 1000]

        if 'RAW百分比' in df_filtered_clean.columns:
            raw_values = pd.to_numeric(df_filtered_clean['RAW百分比'].astype(str).str.replace('%', ''), errors='coerce')
            df_filtered_clean = df_filtered_clean[raw_values <= 1000]

        st.info(f"📊 已自动剔除数值异常值，当前数据量：{len(df_filtered_clean)} 条")

        # 计算分页信息
        total_rows = len(df_filtered_clean)
        rows_per_page = 30
        total_pages = (total_rows + rows_per_page - 1) // rows_per_page

        col1, col2 = st.columns([3, 1])

        with col1:
            current_page = st.selectbox(
                f"选择页码 (共{total_pages}页，每页{rows_per_page}条)",
                options=list(range(1, total_pages + 1)),
                index=0,
                key="chart_page"
            )

        with col2:
            st.write(f"第 {current_page} 页 / 共 {total_pages} 页")

        # 计算当前页数据范围
        start_idx = (current_page - 1) * rows_per_page
        end_idx = min(start_idx + rows_per_page, total_rows)
        df_current = df_filtered_clean.iloc[start_idx:end_idx].copy()

        # 检测异常列
        abnormal_col = None
        for col in df_current.columns:
            if '异常' in col or 'abnormal' in col.lower():
                abnormal_col = col
                break

        # 如果有异常列，标记异常数据
        if abnormal_col:
            # 检查异常列的值：支持是/否、yes/no、true/false等格式
            abnormal_values = df_current[abnormal_col].astype(str).str.lower()
            df_current['是否异常'] = abnormal_values.isin(['是', 'yes', 'true', '异常', '1', 'error', 'err'])
        else:
            # 没有异常列时，默认无异常
            df_current['是否异常'] = False

        # 统计异常数据数量
        abnormal_count = df_current['是否异常'].sum()
        if abnormal_count > 0:
            st.warning(f"⚠️ 检测到 {abnormal_count} 条异常数据，图表中将显示为红色点并断开连线")

        # 显示当前页数据
        with st.expander(f"🔍 查看第{current_page}页数据（共{len(df_current)}条）", expanded=False):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.dataframe(df_current, use_container_width=True, height=300)

            with col2:
                st.write("")
                if st.button("📊 点击查看完整页数据", use_container_width=True):
                    st.dataframe(df_current, use_container_width=True, height=None)

        st.caption(f"📄 当前显示第 {current_page} 页数据，共 {len(df_current)} 条")

        if len(df_current) == 0:
            st.error("❌ 当前页没有数据")
            st.stop()

        st.markdown("---")

        # 图表展示
        st.subheader("📈 图表展示")

        # 图表类型选择
        chart_options = {
            "DIF趋势图": {"y": "DIF百分比", "color": "#26D19C", "title": "DIF数据变化趋势"},
            "RAW趋势图": {"y": "RAW百分比", "color": "#FFA500", "title": "RAW数据变化趋势"},
            "双系列对比": {"y": None, "color": None, "title": "DIF与RAW数据对比"}
        }

        selected_chart = st.radio(
            "选择图表类型",
            options=list(chart_options.keys()),
            horizontal=True,
            help="点击选择要显示的图表"
        )

        st.markdown("")

        # 创建图表
        if selected_chart in ["DIF趋势图", "RAW趋势图"] and chart_options[selected_chart]["y"] in df_current.columns:
            y_col = chart_options[selected_chart]["y"]
            color = chart_options[selected_chart]["color"]
            title = chart_options[selected_chart]["title"]

            # 创建固定X轴：1-30对应每页数据
            df_chart = df_current.copy()
            df_chart['数据点编号'] = range(1, len(df_current) + 1)

            # 添加时间戳到hover显示
            if timestamp_col:
                df_chart['时间戳'] = df_chart[timestamp_col].apply(
                    lambda t: t.strftime('%H:%M:%S') if pd.notna(t) else 'N/A'
                )

            # 添加异常标记到hover
            df_chart['异常标记'] = df_chart['是否异常'].map({True: '⚠️ 异常数据', False: ''})

            # 创建图表
            fig = go.Figure()

            # 分段绘制数据（异常点断开连线）
            df_chart['线段分组'] = 0
            segment_id = 0

            for idx, (i, row) in enumerate(df_chart.iterrows()):
                if row['是否异常']:
                    segment_id += 1
                    df_chart.loc[i, '线段分组'] = segment_id
                else:
                    if idx == 0 or df_chart.iloc[idx-1]['是否异常']:
                        segment_id += 1
                    df_chart.loc[i, '线段分组'] = segment_id

            # 绘制每个线段
            for segment in df_chart['线段分组'].unique():
                segment_data = df_chart[df_chart['线段分组'] == segment]

                # 检查这个段是否包含异常点
                has_abnormal = segment_data['是否异常'].any()

                if has_abnormal and len(segment_data) == 1:
                    # 单个异常点，用红色
                    fig.add_trace(go.Scatter(
                        x=segment_data['数据点编号'],
                        y=segment_data[y_col],
                        mode='markers',
                        name='异常数据',
                        marker=dict(size=12, color='red', symbol='x'),
                        hovertemplate='<b>异常数据</b><br>' +
                                      '数据点: %{x}<br>' +
                                      f'{y_col}: %{{y:.2f}}%<br>' +
                                      ('时间戳: %{customdata[0]}<br>' if timestamp_col else '') +
                                      '<extra></extra>',
                        customdata=segment_data[['时间戳']].values if timestamp_col else [['']] * len(segment_data)
                    ))
                else:
                    # 正常数据段或异常点（但与其他点连接）
                    customdata_cols = []
                    if timestamp_col:
                        customdata_cols.append('时间戳')
                    customdata_cols.append('异常标记')

                    fig.add_trace(go.Scatter(
                        x=segment_data['数据点编号'],
                        y=segment_data[y_col],
                        mode='lines+markers',
                        name='DIF' if y_col == 'DIF百分比' else 'RAW',
                        line=dict(color=color, width=3),
                        marker=dict(size=8, color=color),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                      '数据点: %{x}<br>' +
                                      f'{y_col}: %{{y:.2f}}%<br>' +
                                      ('时间戳: %{customdata[0]}<br>' if timestamp_col else '') +
                                      '<b style="color:red">%{customdata[' + ('1' if timestamp_col else '0') + ']}</b>' +
                                      '<extra></extra>',
                        customdata=segment_data[customdata_cols].values
                    ))

            # 设置X轴：显示时间戳
            if timestamp_col and len(df_current) > 0:
                # 格式化时间戳为时分秒格式
                time_labels = []
                for t in df_current[timestamp_col]:
                    if pd.isna(t):
                        time_labels.append('N/A')
                    else:
                        time_labels.append(t.strftime('%H:%M:%S'))
                fig.update_xaxes(
                    tickmode='array',
                    tickvals=list(range(1, len(df_current) + 1)),
                    ticktext=time_labels,
                    range=[0.5, len(df_current) + 0.5] if len(df_current) < 30 else [0.5, 30.5]
                )
            else:
                # 没有时间戳时显示数据点编号
                fig.update_xaxes(
                    tickmode='linear',
                    tick0=1,
                    dtick=1,
                    range=[0.5, len(df_current) + 0.5] if len(df_current) < 30 else [0.5, 30.5]
                )

            fig.update_layout(
                height=500,
                xaxis_title=f"第{current_page}页数据点",
                yaxis_title=f"{y_col.replace('百分比', '')} (%)",
                hovermode='closest'
            )
            st.plotly_chart(fig, use_container_width=True)

        elif selected_chart == "双系列对比":
            if 'DIF百分比' in df_current.columns and 'RAW百分比' in df_current.columns:
                # 双线图
                fig = make_subplots(
                    rows=1, cols=1,
                    subplot_titles=('📈 DIF与RAW数据对比',)
                )

                # 创建固定X轴：1-30对应每页数据
                df_chart = df_current.copy()
                df_chart['数据点编号'] = range(1, len(df_current) + 1)

                # 添加时间戳到hover显示
                if timestamp_col:
                    df_chart['时间戳'] = df_chart[timestamp_col].apply(
                        lambda t: t.strftime('%H:%M:%S') if pd.notna(t) else 'N/A'
                    )

                # 添加异常标记
                df_chart['异常标记'] = df_chart['是否异常'].map({True: '⚠️ 异常数据', False: ''})

                # 分段绘制DIF数据
                df_chart['DIF线段分组'] = 0
                segment_id = 0

                for idx, (i, row) in enumerate(df_chart.iterrows()):
                    if row['是否异常']:
                        segment_id += 1
                        df_chart.loc[i, 'DIF线段分组'] = segment_id
                    else:
                        if idx == 0 or df_chart.iloc[idx-1]['是否异常']:
                            segment_id += 1
                        df_chart.loc[i, 'DIF线段分组'] = segment_id

                # 绘制DIF线段
                for segment in df_chart['DIF线段分组'].unique():
                    segment_data = df_chart[df_chart['DIF线段分组'] == segment]

                    if segment_data['是否异常'].any() and len(segment_data) == 1:
                        # 单个异常点，用红色
                        fig.add_trace(
                            go.Scatter(
                                x=segment_data['数据点编号'],
                                y=segment_data['DIF百分比'],
                                mode='markers',
                                name='DIF异常',
                                marker=dict(size=10, color='red', symbol='x'),
                                hovertemplate='<b>DIF异常数据</b><br>' +
                                              '数据点: %{x}<br>' +
                                              'DIF百分比: %{y:.2f}%<br>' +
                                              ('时间戳: %{customdata[0]}<br>' if timestamp_col else '') +
                                              '<extra></extra>',
                                customdata=segment_data[['时间戳']].values if timestamp_col else [['']] * len(segment_data),
                                showlegend=True
                            ),
                            row=1, col=1
                        )
                    else:
                        # 正常数据段
                        customdata_cols = []
                        if timestamp_col:
                            customdata_cols.append('时间戳')
                        customdata_cols.append('异常标记')

                        fig.add_trace(
                            go.Scatter(
                                x=segment_data['数据点编号'],
                                y=segment_data['DIF百分比'],
                                mode='lines+markers',
                                name='DIF',
                                line=dict(color='#26D19C', width=3),
                                marker=dict(size=6, color='#26D19C'),
                                hovertemplate='<b>DIF</b><br>' +
                                              '数据点: %{x}<br>' +
                                              'DIF百分比: %{y:.2f}%<br>' +
                                              ('时间戳: %{customdata[0]}<br>' if timestamp_col else '') +
                                              '<b style="color:red">%{customdata[' + ('1' if timestamp_col else '0') + ']}</b>' +
                                              '<extra></extra>',
                                customdata=segment_data[customdata_cols].values,
                                showlegend=True
                            ),
                            row=1, col=1
                        )

                # 分段绘制RAW数据
                df_chart['RAW线段分组'] = 0
                segment_id = 0

                for idx, (i, row) in enumerate(df_chart.iterrows()):
                    if row['是否异常']:
                        segment_id += 1
                        df_chart.loc[i, 'RAW线段分组'] = segment_id
                    else:
                        if idx == 0 or df_chart.iloc[idx-1]['是否异常']:
                            segment_id += 1
                        df_chart.loc[i, 'RAW线段分组'] = segment_id

                # 绘制RAW线段
                for segment in df_chart['RAW线段分组'].unique():
                    segment_data = df_chart[df_chart['RAW线段分组'] == segment]

                    if segment_data['是否异常'].any() and len(segment_data) == 1:
                        # 单个异常点，用红色
                        fig.add_trace(
                            go.Scatter(
                                x=segment_data['数据点编号'],
                                y=segment_data['RAW百分比'],
                                mode='markers',
                                name='RAW异常',
                                marker=dict(size=10, color='red', symbol='diamond'),
                                hovertemplate='<b>RAW异常数据</b><br>' +
                                              '数据点: %{x}<br>' +
                                              'RAW百分比: %{y:.2f}%<br>' +
                                              ('时间戳: %{customdata[0]}<br>' if timestamp_col else '') +
                                              '<extra></extra>',
                                customdata=segment_data[['时间戳']].values if timestamp_col else [['']] * len(segment_data),
                                showlegend=True
                            ),
                            row=1, col=1
                        )
                    else:
                        # 正常数据段
                        customdata_cols = []
                        if timestamp_col:
                            customdata_cols.append('时间戳')
                        customdata_cols.append('异常标记')

                        fig.add_trace(
                            go.Scatter(
                                x=segment_data['数据点编号'],
                                y=segment_data['RAW百分比'],
                                mode='lines+markers',
                                name='RAW',
                                line=dict(color='#FFA500', width=3),
                                marker=dict(size=6, color='#FFA500'),
                                hovertemplate='<b>RAW</b><br>' +
                                              '数据点: %{x}<br>' +
                                              'RAW百分比: %{y:.2f}%<br>' +
                                              ('时间戳: %{customdata[0]}<br>' if timestamp_col else '') +
                                              '<b style="color:red">%{customdata[' + ('1' if timestamp_col else '0') + ']}</b>' +
                                              '<extra></extra>',
                                customdata=segment_data[customdata_cols].values,
                                showlegend=True
                            ),
                            row=1, col=1
                        )

                fig.update_layout(
                    height=500,
                    showlegend=True,
                    hovermode='closest'
                )

                # 设置X轴：显示时间戳
                if timestamp_col and len(df_current) > 0:
                    # 格式化时间戳为时分秒格式
                    time_labels = []
                    for t in df_current[timestamp_col]:
                        if pd.isna(t):
                            time_labels.append('N/A')
                        else:
                            time_labels.append(t.strftime('%H:%M:%S'))
                    fig.update_xaxes(
                        tickmode='array',
                        tickvals=list(range(1, len(df_current) + 1)),
                        ticktext=time_labels,
                        range=[0.5, len(df_current) + 0.5] if len(df_current) < 30 else [0.5, 30.5],
                        title_text=f"第{current_page}页数据点",
                        row=1, col=1
                    )
                else:
                    # 没有时间戳时显示数据点编号
                    fig.update_xaxes(
                        tickmode='linear',
                        tick0=1,
                        dtick=1,
                        range=[0.5, len(df_current) + 0.5] if len(df_current) < 30 else [0.5, 30.5],
                        title_text=f"第{current_page}页数据点",
                        row=1, col=1
                    )
                fig.update_yaxes(title_text="百分比 (%)", row=1, col=1)

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("❌ 数据中缺少DIF百分比或RAW百分比列")


        st.markdown("---")

        # 筛选后数据详情（与图表筛选联动）
        st.markdown("📊 **与图表筛选相同条件下的数据详情**")
        with st.expander("点击查看筛选后的完整数据", expanded=False):
            col1, col2 = st.columns([3, 1])

            with col1:
                if len(df_filtered_clean) > 0:
                    st.dataframe(df_filtered_clean, use_container_width=True, height=300)
                else:
                    st.info("当前筛选条件下没有数据，请调整筛选条件")

            with col2:
                st.write("")
                if len(df_filtered_clean) > 0:
                    if st.button("📊 点击查看完整筛选数据", use_container_width=True):
                        st.dataframe(df_filtered_clean, use_container_width=True, height=None)

        st.markdown("---")

        # 数据导出
        st.subheader("💾 数据导出")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**导出筛选后的数据**")
            if st.button("📥 导出为CSV", use_container_width=True):
                csv = df_filtered.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="✅ 点击下载CSV文件",
                    data=csv,
                    file_name=f"filtered_data_{len(df_filtered)}.csv",
                    mime="text/csv",
                    key="download_csv"
                )

        with col2:
            st.write("**导出当前图表**")
            if st.button("📷 导出为PNG", use_container_width=True):
                # 这里可以添加图表导出功能
                st.info("💡 提示：右键点击图表可选择'导出为PNG'保存图片")

    except Exception as e:
        st.error(f"❌ 读取文件时出错：{str(e)}")
        st.write("请检查CSV文件格式是否正确")

else:
    # 欢迎页面
    st.info("👆 请在左侧上传CSV文件开始分析")

    st.markdown("""
    ### 📖 使用指南

    #### 1️⃣ 数据上传
    - 从KeNaiXin APP导出CSV文件
    - 在左侧面板点击"选择CSV文件"上传

    #### 2️⃣ 数据筛选
    - **入耳状态**: 筛选入耳/出耳数据
    - **用户名**: 选择特定用户
    - **左右耳**: 筛选左耳或右耳数据
    - **⏰ 时间范围**: 筛选指定时间范围内的数据（支持日期范围选择）

    #### 3️⃣ 图表查看
    - **DIF趋势图**: 展示DIF数据变化
    - **RAW趋势图**: 展示RAW数据变化
    - **双系列对比**: 同时显示DIF和RAW，对比更明显
    - **⚠️ 异常数据支持**: CSV中包含"异常"列时，异常数据点显示为红色×标记并断开连线

    #### 4️⃣ 数据交互
    - 点击"数据点详情"查看具体数值
    - 鼠标悬停图表查看详细信息
    - 图表支持缩放、平移等操作
    - **📄 数据分页**: 在"数据分页"中选择页码，图表和当前页数据联动显示

    #### 5️⃣ 数据导出
    - 导出筛选后的CSV数据
    - 右键图表可导出为PNG图片

    ### 📋 支持的CSV字段

    | 字段名 | 说明 | 是否必需 |
    |--------|------|----------|
    | 用户名 | 数据所属用户 | 可选 |
    | MAC地址 | 设备MAC地址 | 推荐 |
    | **时间/时间戳** | **数据时间戳（支持多种格式）** | **🎯 新增：推荐** |
    | DIF百分比 | DIF数据百分比 | **必需** |
    | RAW百分比 | RAW数据百分比 | **必需** |
    | 是否入耳 | 入耳状态 | 可选 |
    | 左右耳 | 左耳/右耳标识 | 可选 |
    | **异常** | **标记异常数据（任意非空值表示异常）** | **🎯 新增：可选** |

    ### ⚡ 快速开始
    1. 点击左侧"📤 文件上传"
    2. 选择CSV文件
    3. 在"🔎 数据筛选"中设置条件（**包括时间范围筛选**）
    4. 在"📈 图表展示"中选择图表类型
    5. 查看图表和数据分析结果

    ### 🆕 新增功能
    - ✅ **时间戳筛选**: 支持按日期范围筛选数据
    - ✅ **时间轴图表**: 自动使用时间戳作为X轴
    - ✅ **多格式支持**: 支持"时间"、"时间戳"、"timestamp"等多种时间列名
    - ✅ **智能识别**: 自动检测并处理时间戳列
    - ✅ **数据分页**: 选择页码后图表显示对应页数据，每页30条，数据量大时性能更好
    """)

# 页脚
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
    "📊 传感器数据图表工具 | KeNaiXin开发团队 | 使用Streamlit构建"
    "</div>",
    unsafe_allow_html=True
)
