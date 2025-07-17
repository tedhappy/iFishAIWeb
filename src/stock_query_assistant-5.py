import os
import asyncio
from typing import Optional
import dashscope
from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
import pandas as pd
from sqlalchemy import create_engine
from qwen_agent.tools.base import BaseTool, register_tool
import matplotlib.pyplot as plt
import io
import base64
import time
import numpy as np
from datetime import datetime, timedelta
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

system_prompt = """我是股票查询助手，以下是关于股票历史价格表 stock_price 的字段，我可能会编写对应的SQL，对数据进行查询
-- 股票历史价格表
CREATE TABLE stock_price (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    stock_name VARCHAR(20) NOT NULL COMMENT '股票名称',
    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    trade_date VARCHAR(10) NOT NULL COMMENT '交易日期',
    open DECIMAL(15,2) COMMENT '开盘价',
    high DECIMAL(15,2) COMMENT '最高价',
    low DECIMAL(15,2) COMMENT '最低价',
    close DECIMAL(15,2) COMMENT '收盘价',
    vol DECIMAL(20,2) COMMENT '成交量',
    amount DECIMAL(20,2) COMMENT '成交额',
    UNIQUE KEY uniq_stock_date (ts_code, trade_date)
);
我将回答用户关于股票历史价格的相关问题。
每当 exc_sql 工具返回 markdown 表格和图片时，你必须原样输出工具返回的全部内容（包括图片 markdown），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。
如果是预测未来价格，需要对未来的价格进行详细的解释说明，比如价格将持续走高，或价格将相对平稳，或价格将持续走低。
"""

# exc_sql工具
@register_tool('exc_sql')
class ExcSQLTool(BaseTool):
    description = '对于生成的SQL，进行SQL查询，并自动可视化'
    parameters = [
        {
            'name': 'sql_input',
            'type': 'string',
            'description': '生成的SQL语句',
            'required': True
        },
        {
            'name': 'need_visualize',
            'type': 'boolean',
            'description': '是否需要可视化和统计信息，默认True。如果是对比分析等场景可设为False，不进行可视化。',
            'required': False,
            'default': True
        }
    ]
    def call(self, params: str, **kwargs) -> str:
        import json
        import matplotlib.pyplot as plt
        import io, os, time
        import numpy as np
        args = json.loads(params)
        sql_input = args['sql_input']
        database = args.get('database', 'stock')
        engine = create_engine(
            f"mysql+mysqlconnector://student123:student321@rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com:3306/{database}?charset=utf8mb4",
            connect_args={'connect_timeout': 10}, pool_size=10, max_overflow=20
        )
        try:
            df = pd.read_sql(sql_input, engine)
            # 前5行+后5行拼接展示
            if len(df) > 10:
                md = pd.concat([df.head(5), df.tail(5)]).to_markdown(index=False)
            else:
                md = df.to_markdown(index=False)
            # 只返回表格
            if len(df) == 1:
                return md
            need_visualize = args.get('need_visualize', True)
            if not need_visualize:
                return md
            desc_md = df.describe().to_markdown()
            # 自动创建目录
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'stock_{int(time.time()*1000)}.png'
            save_path = os.path.join(save_dir, filename)
            # 智能选择可视化方式
            generate_smart_chart_png(df, save_path)
            img_path = os.path.join('image_show', filename)
            img_md = f'![图表]({img_path})'
            return f"{md}\n\n{desc_md}\n\n{img_md}"
        except Exception as e:
            return f"SQL执行或可视化出错: {str(e)}"

def generate_smart_chart_png(df_sql, save_path):
    columns = df_sql.columns
    if len(df_sql) == 0 or len(columns) < 2:
        plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, '无可视化数据', ha='center', va='center', fontsize=16)
        plt.axis('off')
        plt.savefig(save_path)
        plt.close()
        return
    x_col = columns[0]
    y_cols = columns[1:]
    x = df_sql[x_col]
    # 如果数据点较多，自动采样10个点
    if len(df_sql) > 20:
        idx = np.linspace(0, len(df_sql) - 1, 10, dtype=int)
        x = x.iloc[idx]
        df_plot = df_sql.iloc[idx]
        chart_type = 'line'
    else:
        df_plot = df_sql
        chart_type = 'bar'
    plt.figure(figsize=(10, 6))
    for y_col in y_cols:
        if chart_type == 'bar':
            plt.bar(df_plot[x_col], df_plot[y_col], label=str(y_col))
        else:
            plt.plot(df_plot[x_col], df_plot[y_col], marker='o', label=str(y_col))
    plt.xlabel(x_col)
    plt.ylabel('数值')
    plt.title('股票数据统计')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

# arima_stock工具
@register_tool('arima_stock')
class ArimaStockTool(BaseTool):
    description = '对指定股票(ts_code)的收盘价进行ARIMA(5,1,5)建模，并预测未来n天的价格，返回预测表格和折线图。'
    parameters = [
        {
            'name': 'ts_code',
            'type': 'string',
            'description': '股票代码，必填',
            'required': True
        },
        {
            'name': 'n',
            'type': 'integer',
            'description': '预测未来天数，必填',
            'required': True
        }
    ]
    def call(self, params: str, **kwargs) -> str:
        import json
        args = json.loads(params)
        ts_code = args['ts_code']
        n = int(args['n'])
        # 获取今天和一年前的日期
        today = datetime.now().date()
        start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        # 连接MySQL，获取历史收盘价
        engine = create_engine(
            f"mysql+mysqlconnector://student123:student321@rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com:3306/stock?charset=utf8mb4",
            connect_args={'connect_timeout': 10}, pool_size=10, max_overflow=20
        )
        sql = f"""
            SELECT trade_date, close FROM stock_price
            WHERE ts_code = '{ts_code}' AND trade_date >= '{start_date}' AND trade_date < '{end_date}'
            ORDER BY trade_date ASC
        """
        df = pd.read_sql(sql, engine)
        if len(df) < 30:
            return '历史数据不足，无法进行ARIMA建模预测。'
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])
        # ARIMA建模
        try:
            model = ARIMA(df['close'], order=(5,1,5))
            model_fit = model.fit()
            forecast = model_fit.forecast(steps=n)
            # 生成预测日期
            last_date = pd.to_datetime(df['trade_date'].iloc[-1])
            pred_dates = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(n)]
            pred_df = pd.DataFrame({'预测日期': pred_dates, '预测收盘价': forecast})
            # 保存预测图
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'arima_{ts_code}_{int(time.time()*1000)}.png'
            save_path = os.path.join(save_dir, filename)
            plt.figure(figsize=(10,6))
            plt.plot(df['trade_date'], df['close'], label='历史收盘价')
            plt.plot(pred_df['预测日期'], pred_df['预测收盘价'], marker='o', label='预测收盘价')
            plt.xlabel('日期')
            plt.ylabel('收盘价')
            plt.title(f'{ts_code} 收盘价ARIMA预测')
            plt.legend()
            # 横坐标自动稀疏显示
            all_dates = list(df['trade_date']) + list(pred_df['预测日期'])
            total_len = len(all_dates)
            if total_len > 12:
                step = max(1, total_len // 10)
                show_idx = list(range(0, total_len, step))
                show_labels = [all_dates[i] for i in show_idx]
                plt.xticks(show_idx, show_labels, rotation=45)
            else:
                plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(save_path)
            plt.close()
            img_path = os.path.join('image_show', filename)
            img_md = f'![ARIMA预测]({img_path})'
            return f"{pred_df.to_markdown(index=False)}\n\n{img_md}"
        except Exception as e:
            return f'ARIMA建模或预测出错: {str(e)}'

# boll_detection工具
@register_tool('boll_detection')
class BollDetectionTool(BaseTool):
    description = '对指定股票(ts_code)的收盘价进行布林带异常点检测，默认检测过去1年，也可自定义时间范围，返回超买和超卖日期及布林带图。'
    parameters = [
        {
            'name': 'ts_code',
            'type': 'string',
            'description': '股票代码，必填',
            'required': True
        },
        {
            'name': 'start_date',
            'type': 'string',
            'description': '检测起始日期，格式YYYY-MM-DD，选填',
            'required': False
        },
        {
            'name': 'end_date',
            'type': 'string',
            'description': '检测结束日期，格式YYYY-MM-DD，选填',
            'required': False
        }
    ]
    def call(self, params: str, **kwargs) -> str:
        import json
        args = json.loads(params)
        ts_code = args['ts_code']
        today = datetime.now().date()
        # 处理日期范围
        if 'start_date' in args and args['start_date']:
            start_date = args['start_date']
        else:
            start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        if 'end_date' in args and args['end_date']:
            end_date = args['end_date']
        else:
            end_date = today.strftime('%Y-%m-%d')
        # 获取数据
        engine = create_engine(
            f"mysql+mysqlconnector://student123:student321@rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com:3306/stock?charset=utf8mb4",
            connect_args={'connect_timeout': 10}, pool_size=10, max_overflow=20
        )
        sql = f"""
            SELECT trade_date, close FROM stock_price
            WHERE ts_code = '{ts_code}' AND trade_date >= '{start_date}' AND trade_date <= '{end_date}'
            ORDER BY trade_date ASC
        """
        df = pd.read_sql(sql, engine)
        if len(df) < 21:
            return '历史数据不足，无法进行布林带检测。'
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])
        # 计算布林带
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['STD20'] = df['close'].rolling(window=20).std()
        df['UPPER'] = df['MA20'] + 2 * df['STD20']
        df['LOWER'] = df['MA20'] - 2 * df['STD20']
        # 检测超买/超卖
        overbought = df[df['close'] > df['UPPER']][['trade_date', 'close']]
        oversold = df[df['close'] < df['LOWER']][['trade_date', 'close']]
        # 结果表格
        result_md = f"### 超买日期\n{overbought.to_markdown(index=False)}\n\n### 超卖日期\n{oversold.to_markdown(index=False)}"
        # 绘制布林带图
        save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
        os.makedirs(save_dir, exist_ok=True)
        filename = f'boll_{ts_code}_{int(time.time()*1000)}.png'
        save_path = os.path.join(save_dir, filename)
        plt.figure(figsize=(12,6))
        plt.plot(df['trade_date'], df['close'], label='收盘价')
        plt.plot(df['trade_date'], df['MA20'], label='MA20')
        plt.plot(df['trade_date'], df['UPPER'], label='上轨+2σ')
        plt.plot(df['trade_date'], df['LOWER'], label='下轨-2σ')
        plt.fill_between(df['trade_date'], df['UPPER'], df['LOWER'], color='gray', alpha=0.1)
        plt.scatter(overbought['trade_date'], overbought['close'], color='red', label='超买', zorder=5)
        plt.scatter(oversold['trade_date'], oversold['close'], color='blue', label='超卖', zorder=5)
        # 横坐标稀疏显示
        total_len = len(df)
        if total_len > 12:
            step = max(1, total_len // 10)
            show_idx = list(range(0, total_len, step))
            show_labels = [df['trade_date'].iloc[i] for i in show_idx]
            plt.xticks(show_idx, show_labels, rotation=45)
        else:
            plt.xticks(rotation=45)
        plt.xlabel('日期')
        plt.ylabel('价格')
        plt.title(f'{ts_code} 布林带异常点检测')
        plt.legend()
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        img_path = os.path.join('image_show', filename)
        img_md = f'![布林带检测]({img_path})'
        return f"{result_md}\n\n{img_md}"

# prophet_analysis工具
@register_tool('prophet_analysis')
class ProphetAnalysisTool(BaseTool):
    description = '对指定股票(ts_code)的收盘价进行Prophet周期性分析，分解trend、weekly、yearly并可视化，支持自定义时间范围。'
    parameters = [
        {
            'name': 'ts_code',
            'type': 'string',
            'description': '股票代码，必填',
            'required': True
        },
        {
            'name': 'start_date',
            'type': 'string',
            'description': '分析起始日期，格式YYYY-MM-DD，选填',
            'required': False
        },
        {
            'name': 'end_date',
            'type': 'string',
            'description': '分析结束日期，格式YYYY-MM-DD，选填',
            'required': False
        }
    ]
    def call(self, params: str, **kwargs) -> str:
        import json
        args = json.loads(params)
        ts_code = args['ts_code']
        today = datetime.now().date()
        # 处理日期范围
        if 'start_date' in args and args['start_date']:
            start_date = args['start_date']
        else:
            start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        if 'end_date' in args and args['end_date']:
            end_date = args['end_date']
        else:
            end_date = today.strftime('%Y-%m-%d')
        # 获取数据
        engine = create_engine(
            f"mysql+mysqlconnector://student123:student321@rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com:3306/stock?charset=utf8mb4",
            connect_args={'connect_timeout': 10}, pool_size=10, max_overflow=20
        )
        sql = f"""
            SELECT trade_date, close FROM stock_price
            WHERE ts_code = '{ts_code}' AND trade_date >= '{start_date}' AND trade_date <= '{end_date}'
            ORDER BY trade_date ASC
        """
        df = pd.read_sql(sql, engine)
        if len(df) < 30:
            return '历史数据不足，无法进行Prophet周期性分析。'
        df['ds'] = pd.to_datetime(df['trade_date'])
        df['y'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['y'])
        # Prophet建模
        try:
            m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
            m.fit(df[['ds', 'y']])
            future = m.make_future_dataframe(periods=0)
            forecast = m.predict(future)
            # 保存分解图
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'prophet_{ts_code}_{int(time.time()*1000)}.png'
            save_path = os.path.join(save_dir, filename)
            fig = m.plot_components(forecast)
            fig.savefig(save_path)
            plt.close(fig)
            img_path = os.path.join('image_show', filename)
            img_md = f'![Prophet周期分解]({img_path})'
            return f"Prophet周期性分解（趋势、周、年）：\n\n{img_md}"
        except Exception as e:
            return f'Prophet建模或分解出错: {str(e)}'

def init_agent_service():
    llm_cfg = {
        'model': 'qwen-turbo-2025-04-28',
        'timeout': 30,
        'retry_count': 3,
    }
    # MCP 工具配置
    tools = [{
        "mcpServers": {
            "tavily-mcp": {
                "command": "npx",
                "args": ["-y", "tavily-mcp@0.1.4"],
                "env": {
                    "TAVILY_API_KEY": "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"
                },
                "disabled": False,
                "autoApprove": []
            }
        }
    }, 'exc_sql', 'arima_stock', 'boll_detection', 'prophet_analysis']

    try:
        bot = Assistant(
            llm=llm_cfg,
            name='股票查询助手',
            description='股票历史价格查询与分析',
            system_message=system_prompt,
            function_list=tools,
            files = ['./faq.txt']
        )
        print("助手初始化成功！")
        return bot
    except Exception as e:
        print(f"助手初始化失败: {str(e)}")
        raise

def app_tui():
    try:
        bot = init_agent_service()
        messages = []
        while True:
            try:
                query = input('user question: ')
                file = input('file url (press enter if no file): ').strip()
                if not query:
                    print('user question cannot be empty！')
                    continue
                if not file:
                    messages.append({'role': 'user', 'content': query})
                else:
                    messages.append({'role': 'user', 'content': [{'text': query}, {'file': file}]})
                print("正在处理您的请求...")
                response = []
                for resp in bot.run(messages):
                    print('bot response:', resp)
                messages.extend(response)
            except Exception as e:
                print(f"处理请求时出错: {str(e)}")
                print("请重试或输入新的问题")
    except Exception as e:
        print(f"启动终端模式失败: {str(e)}")

def app_gui():
    try:
        print("正在启动 Web 界面...")
        bot = init_agent_service()
        chatbot_config = {
            'prompt.suggestions': [
                '查询2024年全年贵州茅台的收盘价走势',
                '统计2024年4月国泰君安的日均成交量',
                '对比2024年中芯国际和贵州茅台的涨跌幅',
                '预测贵州茅台未来7天的收盘价',
                '检测贵州茅台近一年超买超卖点',
                '分析贵州茅台近一年周期性规律',
                '贵州茅台最近的热点新闻',
            ]
        }
        print("Web 界面准备就绪，正在启动服务...")
        WebUI(
            bot,
            chatbot_config=chatbot_config
        ).run()
    except Exception as e:
        print(f"启动 Web 界面失败: {str(e)}")
        print("请检查网络连接和 API Key 配置")

if __name__ == '__main__':
    app_gui()  # 默认启动Web界面 
    #app_tui() 