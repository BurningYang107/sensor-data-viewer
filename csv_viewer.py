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

# 处理文件读取
if uploaded_file is not None:
    try:
        # 读取CSV
        df = pd.read_csv(uploaded_file)

        # 数据概览
        st.subheader("📋 数据概览")
        col1, col2, col3 = st.columns(3)
        col1.metric("总数据量", len(df))
        col2.metric("入耳数据", len(df[df['是否入耳'] == '是']) if '是否入耳' in df.columns else "N/A")
        col3.metric("出耳数据", len(df[df['是否入耳'] == '否']) if '是否入耳' in df.columns else "N/A")

        # 数据预览
        with st.expander("🔍 查看原始数据", expanded=False):
            st.dataframe(df, use_container_width=True, height=300)

        st.markdown("---")

        # 数据筛选
        st.subheader("🔎 数据筛选")

        # 筛选器容器
        filter_cols = st.columns(3)

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
            if '左右耳' in df_filtered.columns:
                ear_side = st.multiselect(
                    "左右耳",
                    options=df_filtered['左右耳'].unique(),
                    default=df_filtered['左右耳'].unique(),
                    help="选择左耳或右耳数据"
                )
                df_filtered = df_filtered[df_filtered['左右耳'].isin(ear_side)]

        st.markdown("")
        st.write(f"✅ 筛选后数据量：{len(df_filtered)} 条")

        if len(df_filtered) == 0:
            st.error("❌ 筛选后没有数据，请调整筛选条件")
            st.stop()

        st.markdown("---")

        # 图表展示
        st.subheader("📈 图表展示")

        # 图表类型选择
        chart_options = {
            "DIF趋势图": {"y": "DIF百分比", "color": "#26D19C", "title": "DIF数据变化趋势"},
            "RAW趋势图": {"y": "RAW百分比", "color": "#FFA500", "title": "RAW数据变化趋势"},
            "双系列对比": {"y": None, "color": None, "title": "DIF与RAW数据对比"},
            "散点图": {"y": "RAW百分比", "color": "是否入耳", "title": "DIF vs RAW 散点图"}
        }

        selected_chart = st.radio(
            "选择图表类型",
            options=list(chart_options.keys()),
            horizontal=True,
            help="点击选择要显示的图表"
        )

        st.markdown("")

        # 创建图表
        if selected_chart in ["DIF趋势图", "RAW趋势图"] and chart_options[selected_chart]["y"] in df_filtered.columns:
            y_col = chart_options[selected_chart]["y"]
            color = chart_options[selected_chart]["color"]
            title = chart_options[selected_chart]["title"]

            fig = px.line(
                df_filtered,
                x=df_filtered.index if '时间' not in df_filtered.columns else '时间',
                y=y_col,
                title=title,
                labels={
                    y_col: f'{y_col.replace("百分比", "")} (%)',
                    'index': '数据序号' if '时间' not in df_filtered.columns else '时间'
                },
                markers=True,
                hover_data=[col for col in ['用户名', 'MAC地址', '左右耳', '是否入耳'] if col in df_filtered.columns]
            )
            fig.update_traces(
                line=dict(color=color, width=3),
                marker=dict(size=8, color=color)
            )
            fig.update_layout(
                height=500,
                xaxis_title="数据点" if '时间' not in df_filtered.columns else "时间",
                yaxis_title=f"{y_col.replace('百分比', '')} (%)",
                hovermode='closest'
            )
            st.plotly_chart(fig, use_container_width=True)

        elif selected_chart == "双系列对比":
            if 'DIF百分比' in df_filtered.columns and 'RAW百分比' in df_filtered.columns:
                # 双线图
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('📈 数据趋势对比', '📊 数据点分布'),
                    vertical_spacing=0.12,
                    row_heights=[0.7, 0.3]
                )

                # DIF线
                x_data = df_filtered.index if '时间' not in df_filtered.columns else df_filtered['时间']
                fig.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=df_filtered['DIF百分比'],
                        mode='lines+markers',
                        name='DIF',
                        line=dict(color='#26D19C', width=3),
                        marker=dict(size=6)
                    ),
                    row=1, col=1
                )

                # RAW线
                fig.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=df_filtered['RAW百分比'],
                        mode='lines+markers',
                        name='RAW',
                        line=dict(color='#FFA500', width=3),
                        marker=dict(size=6)
                    ),
                    row=1, col=1
                )

                # 散点图
                fig.add_trace(
                    go.Scatter(
                        x=df_filtered['DIF百分比'],
                        y=df_filtered['RAW百分比'],
                        mode='markers',
                        name='DIF vs RAW',
                        marker=dict(
                            size=10,
                            color='#9370DB',
                            opacity=0.7,
                            line=dict(width=1, color='white')
                        ),
                        text=[f"点#{i+1}" for i in df_filtered.index],
                        hovertemplate='<b>%{text}</b><br>DIF: %{x}%<br>RAW: %{y}%<extra></extra>'
                    ),
                    row=2, col=1
                )

                fig.update_layout(
                    height=700,
                    showlegend=True,
                    hovermode='closest'
                )
                fig.update_xaxes(title_text="数据序号" if '时间' not in df_filtered.columns else "时间", row=1, col=1)
                fig.update_yaxes(title_text="百分比 (%)", row=1, col=1)
                fig.update_xaxes(title_text="DIF (%)", row=2, col=1)
                fig.update_yaxes(title_text="RAW (%)", row=2, col=1)

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("❌ 数据中缺少DIF百分比或RAW百分比列")

        elif selected_chart == "散点图":
            if 'DIF百分比' in df_filtered.columns and 'RAW百分比' in df_filtered.columns:
                fig = px.scatter(
                    df_filtered,
                    x='DIF百分比',
                    y='RAW百分比',
                    color='是否入耳' if '是否入耳' in df_filtered.columns else None,
                    size='左右耳' if '左右耳' in df_filtered.columns else None,
                    hover_data=['时间' if '时间' in df_filtered.columns else df_filtered.index, '用户名', 'MAC地址'],
                    title="DIF vs RAW 散点图",
                    labels={
                        'DIF百分比': 'DIF (%)',
                        'RAW百分比': 'RAW (%)'
                    }
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("❌ 数据中缺少DIF百分比或RAW百分比列")

        st.markdown("---")

        # 数据点详情
        st.subheader("🔍 数据点详情")

        with st.expander("点击查看具体数据点", expanded=False):
            if len(df_filtered) > 0:
                # 选择数据点
                point_options = []
                for i in df_filtered.index[:100]:  # 最多显示100个点
                    dif_val = df_filtered.loc[i, 'DIF百分比'] if 'DIF百分比' in df_filtered.columns else "N/A"
                    raw_val = df_filtered.loc[i, 'RAW百分比'] if 'RAW百分比' in df_filtered.columns else "N/A"
                    point_options.append(f"点 #{i+1} (DIF: {dif_val}%, RAW: {raw_val}%)")

                if len(df_filtered) > 100:
                    point_options.append("... (还有更多数据点)")

                selected_idx = st.selectbox(
                    "选择数据点",
                    options=list(df_filtered.index[:100]),
                    format_func=lambda x: f"点 #{x+1} (DIF: {df_filtered.loc[x, 'DIF百分比']}%, RAW: {df_filtered.loc[x, 'RAW百分比']}%)" if 'DIF百分比' in df_filtered.columns and 'RAW百分比' in df_filtered.columns else f"点 #{x+1}"
                )

                if selected_idx is not None:
                    row_data = df_filtered.loc[selected_idx]

                    # 显示详情
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**📋 基础信息**")
                        for col in ['用户名', 'MAC地址', '左右耳', '时间', '是否入耳']:
                            if col in row_data and pd.notna(row_data[col]):
                                st.write(f"• **{col}**: {row_data[col]}")

                    with col2:
                        st.write("**📊 传感器数据**")
                        for col in ['DIF原始', 'DIF数值', 'DIF百分比', 'RAW原始', 'RAW数值', 'RAW百分比']:
                            if col in row_data and pd.notna(row_data[col]):
                                st.write(f"• **{col}**: {row_data[col]}")

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

    #### 3️⃣ 图表查看
    - **DIF趋势图**: 展示DIF数据变化
    - **RAW趋势图**: 展示RAW数据变化
    - **双系列对比**: 同时显示DIF和RAW，对比更明显
    - **散点图**: 分析DIF和RAW的相关性

    #### 4️⃣ 数据交互
    - 点击"数据点详情"查看具体数值
    - 鼠标悬停图表查看详细信息
    - 图表支持缩放、平移等操作

    #### 5️⃣ 数据导出
    - 导出筛选后的CSV数据
    - 右键图表可导出为PNG图片

    ### 📋 支持的CSV字段

    | 字段名 | 说明 | 是否必需 |
    |--------|------|----------|
    | 用户名 | 数据所属用户 | 可选 |
    | MAC地址 | 设备MAC地址 | 推荐 |
    | 时间 | 数据时间戳 | 推荐 |
    | DIF百分比 | DIF数据百分比 | **必需** |
    | RAW百分比 | RAW数据百分比 | **必需** |
    | 是否入耳 | 入耳状态 | 可选 |
    | 左右耳 | 左耳/右耳标识 | 可选 |

    ### ⚡ 快速开始
    1. 点击左侧"📤 文件上传"
    2. 选择CSV文件
    3. 在"🔎 数据筛选"中设置条件
    4. 在"📈 图表展示"中选择图表类型
    5. 查看图表和数据分析结果
    """)

# 页脚
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
    "📊 传感器数据图表工具 | KeNaiXin开发团队 | 使用Streamlit构建"
    "</div>",
    unsafe_allow_html=True
)
