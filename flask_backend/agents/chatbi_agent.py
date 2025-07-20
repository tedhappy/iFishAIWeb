from .base_agent import BaseAgent
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
import pandas as pd
from sqlalchemy import create_engine
import matplotlib
# 设置非交互式后端，避免GUI相关错误
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import os
import time
import json
import numpy as np
from typing import List
from utils.logger import logger
from datetime import datetime, timedelta
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 通用图表生成函数
def generate_smart_chart_png(df_sql, save_path):
    """智能选择可视化方式"""
    
    logger.info(f"[图表生成] 开始生成图表，数据行数: {len(df_sql)}, 列数: {len(df_sql.columns)}, 保存路径: {save_path}")
    
    columns = df_sql.columns
    if len(df_sql) == 0 or len(columns) < 2:
        logger.warning(f"[图表生成] 数据不足，无法生成有效图表")
        plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, '无可视化数据', ha='center', va='center', fontsize=16)
        plt.axis('off')
        plt.savefig(save_path)
        plt.close()
        logger.info(f"[图表生成] 已生成空数据提示图表: {save_path}")
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
        logger.info(f"[图表生成] 数据点较多({len(df_sql)}行)，采样为10个点，使用折线图")
    else:
        df_plot = df_sql
        chart_type = 'bar'
        logger.info(f"[图表生成] 数据点较少({len(df_sql)}行)，使用柱状图")
    
    logger.info(f"[图表生成] X轴: {x_col}, Y轴: {list(y_cols)}, 图表类型: {chart_type}")
    
    plt.figure(figsize=(10, 6))
    for y_col in y_cols:
        if chart_type == 'bar':
            plt.bar(df_plot[x_col], df_plot[y_col], label=str(y_col))
        else:
            plt.plot(df_plot[x_col], df_plot[y_col], marker='o', label=str(y_col))
    plt.xlabel(x_col)
    plt.ylabel('数值')
    plt.title('数据统计')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    
    logger.info(f"[图表生成] 图表生成完成并保存到: {save_path}")

# 注册通用SQL执行工具
@register_tool('stock_sql')
class StockSQLTool(BaseTool):
    """股票数据SQL查询工具，专门用于股票数据分析"""
    description = '对于生成的SQL，进行SQL查询，并自动可视化'
    parameters = [{
        'name': 'sql_input',
        'type': 'string',
        'description': '生成的SQL语句',
        'required': True
    }, {
        'name': 'need_visualize',
        'type': 'boolean',
        'description': '是否需要可视化和统计信息，默认True。如果是对比分析等场景可设为False，不进行可视化。',
        'required': False,
        'default': True
    }, {
        'name': 'database',
        'type': 'string',
        'description': '数据库名称，默认为stock，可选ubr等',
        'required': False,
        'default': 'stock'
    }]

    def call(self, params: str, **kwargs) -> str:
        logger.info(f"ExcSQLTool开始执行 - 参数: {params[:200]}...")
        
        # 获取状态回调函数
        status_callback = kwargs.get('status_callback')
        
        # 发送工具开始状态
        if status_callback:
            try:
                status_callback({
                    'type': 'tool_start',
                    'message': f'正在执行SQL查询和数据可视化，请稍候...',
                    'tool_name': 'StockSQLTool'
                })
            except Exception as e:
                logger.warning(f'SQL工具状态回调失败: {e}')
        
        try:
            args = json.loads(params)
            sql_input = args['sql_input']
            database = args.get('database', 'stock')
            need_visualize = args.get('need_visualize', True)
            
            logger.info(f"解析SQL参数成功 - 数据库: {database}, 可视化: {need_visualize}")
            
            engine = create_engine(
                f"mysql+mysqlconnector://student123:student321@rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com:3306/{database}?charset=utf8mb4",
                connect_args={'connect_timeout': 10}, pool_size=10, max_overflow=20
            )
            
            try:
                df = pd.read_sql(sql_input, engine)
                logger.info(f"SQL查询执行成功 - 返回行数: {len(df)}, 列数: {len(df.columns)}")
                
                # 前5行+后5行拼接展示
                if len(df) > 10:
                    md = pd.concat([df.head(5), df.tail(5)]).to_markdown(index=False)
                else:
                    md = df.to_markdown(index=False)
                
                # 只返回表格
                if len(df) == 1 or not need_visualize:
                    # 发送工具完成状态（无图表）
                    if status_callback:
                        try:
                            status_callback({
                            'type': 'success',
                            'message': f'SQL查询完成',
                            'tool_name': 'StockSQLTool',
                            'result': md
                        })
                        except Exception as e:
                            logger.warning(f'SQL工具完成状态回调失败: {e}')
                    return md
                
                desc_md = df.describe().to_markdown()
                
                # 生成图表
                save_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
                os.makedirs(save_dir, exist_ok=True)
                filename = f'sql_chart_{int(time.time()*1000)}.png'
                save_path = os.path.join(save_dir, filename)
                
                # 智能选择可视化方式
                generate_smart_chart_png(df, save_path)
                
                img_url = f'/flask/static/images/{filename}'
                img_md = f'![图表]({img_url})'
                
                result = f"{md}\n\n{desc_md}\n\n{img_md}"
                
                # 发送工具完成状态（有图表）
                if status_callback:
                    try:
                        status_callback({
                        'type': 'success',
                        'message': f'SQL查询和数据可视化完成',
                        'tool_name': 'StockSQLTool',
                        'result': result
                    })
                    except Exception as e:
                        logger.warning(f'SQL工具完成状态回调失败: {e}')
                
                return result
                
            except Exception as e:
                logger.error(f"SQL执行错误: {str(e)}")
                error_msg = f"SQL执行或可视化出错: {str(e)}"
                
                # 发送工具错误状态
                if status_callback:
                    try:
                        status_callback({
                            'type': 'error',
                            'message': f'SQL查询失败: {str(e)}',
                            'tool_name': 'StockSQLTool'
                        })
                    except Exception as e:
                        logger.warning(f'SQL工具错误状态回调失败: {e}')
                
                return error_msg
            finally:
                engine.dispose()
                
        except Exception as e:
            logger.error(f"ExcSQLTool执行异常: {str(e)}")
            error_msg = f"工具执行错误: {str(e)}"
            
            # 发送工具错误状态
            if status_callback:
                try:
                    status_callback({
                        'type': 'error',
                        'message': f'SQL工具执行失败: {str(e)}',
                        'tool_name': 'StockSQLTool'
                    })
                except Exception as e:
                    logger.warning(f'SQL工具错误状态回调失败: {e}')
            
            return error_msg

# 注册ARIMA股票预测工具
@register_tool('arima_stock')
class ArimaStockTool(BaseTool):
    """ARIMA股票价格预测工具"""
    description = '对指定股票(ts_code)的收盘价进行ARIMA(5,1,5)建模，并预测未来n天的价格，返回预测表格和折线图。'
    parameters = [{
        'name': 'ts_code',
        'type': 'string',
        'description': '股票代码，必填',
        'required': True
    }, {
        'name': 'n',
        'type': 'integer',
        'description': '预测未来天数，必填',
        'required': True
    }]
    
    def call(self, params: str, **kwargs) -> str:
        logger.info(f"ArimaStockTool开始执行 - 参数: {params}")
        
        # 获取状态回调函数
        status_callback = kwargs.get('status_callback')
        
        # 发送工具开始状态
        if status_callback:
            try:
                status_callback({
                    'type': 'tool_start',
                    'message': f'正在进行ARIMA预测分析，请稍候...',
                    'tool_name': 'ArimaStockTool'
                })
            except Exception as e:
                logger.warning(f'ARIMA工具状态回调失败: {e}')
        
        try:
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
            engine.dispose()
            
            if len(df) < 30:
                return '历史数据不足，无法进行ARIMA建模预测。'
            
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df = df.dropna(subset=['close'])
            
            # ARIMA建模
            model = ARIMA(df['close'], order=(5,1,5))
            model_fit = model.fit()
            forecast = model_fit.forecast(steps=n)
            
            # 生成预测日期
            last_date = pd.to_datetime(df['trade_date'].iloc[-1])
            pred_dates = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(n)]
            pred_df = pd.DataFrame({'预测日期': pred_dates, '预测收盘价': forecast})
            
            # 保存预测图
            save_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
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
            
            img_url = f'/flask/static/images/{filename}'
            img_md = f'![ARIMA预测]({img_url})'
            
            result = f"{pred_df.to_markdown(index=False)}\n\n{img_md}"
            
            # 发送工具完成状态
            if status_callback:
                try:
                    status_callback({
                        'type': 'success',
                        'message': f'ARIMA预测分析完成',
                        'tool_name': 'ArimaStockTool',
                        'result': result
                    })
                except Exception as e:
                    logger.warning(f'ARIMA工具完成状态回调失败: {e}')
            
            return result
            
        except Exception as e:
            logger.error(f"ARIMA建模或预测出错: {str(e)}")
            error_msg = f'ARIMA建模或预测出错: {str(e)}'
            
            # 发送工具错误状态
            if status_callback:
                try:
                    status_callback({
                        'type': 'error',
                        'message': f'ARIMA预测分析失败: {str(e)}',
                        'tool_name': 'ArimaStockTool'
                    })
                except Exception as e:
                    logger.warning(f'ARIMA工具错误状态回调失败: {e}')
            
            return error_msg

# 注册布林带检测工具
@register_tool('boll_detection')
class BollDetectionTool(BaseTool):
    """布林带异常点检测工具"""
    description = '对指定股票(ts_code)的收盘价进行布林带异常点检测，默认检测过去1年，也可自定义时间范围，返回超买和超卖日期及布林带图。'
    parameters = [{
        'name': 'ts_code',
        'type': 'string',
        'description': '股票代码，必填',
        'required': True
    }, {
        'name': 'start_date',
        'type': 'string',
        'description': '检测起始日期，格式YYYY-MM-DD，选填',
        'required': False
    }, {
        'name': 'end_date',
        'type': 'string',
        'description': '检测结束日期，格式YYYY-MM-DD，选填',
        'required': False
    }]
    
    def call(self, params: str, **kwargs) -> str:
        logger.info(f"BollDetectionTool开始执行 - 参数: {params}")
        
        # 获取状态回调函数
        status_callback = kwargs.get('status_callback')
        
        # 发送工具开始状态
        if status_callback:
            try:
                status_callback({
                    'type': 'tool_start',
                    'message': f'正在进行布林带异常点检测，请稍候...',
                    'tool_name': 'BollDetectionTool'
                })
            except Exception as e:
                logger.warning(f'布林带工具状态回调失败: {e}')
        
        try:
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
            engine.dispose()
            
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
            save_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
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
            
            img_url = f'/flask/static/images/{filename}'
            img_md = f'![布林带检测]({img_url})'
            
            result = f"{result_md}\n\n{img_md}"
            
            # 发送工具完成状态
            if status_callback:
                try:
                    status_callback({
                        'type': 'success',
                        'message': f'布林带异常点检测完成',
                        'tool_name': 'BollDetectionTool',
                        'result': result
                    })
                except Exception as e:
                    logger.warning(f'布林带工具完成状态回调失败: {e}')
            
            return result
            
        except Exception as e:
            logger.error(f"布林带检测出错: {str(e)}")
            error_msg = f"布林带检测出错: {str(e)}"
            
            # 发送工具错误状态
            if status_callback:
                try:
                    status_callback({
                        'type': 'error',
                        'message': f'布林带异常点检测失败: {str(e)}',
                        'tool_name': 'BollDetectionTool'
                    })
                except Exception as e:
                    logger.warning(f'布林带工具错误状态回调失败: {e}')
            
            return error_msg

# 注册Prophet周期性分析工具
@register_tool('prophet_analysis')
class ProphetAnalysisTool(BaseTool):
    """Prophet周期性分析工具"""
    description = '对指定股票(ts_code)的收盘价进行Prophet周期性分析，分解trend、weekly、yearly并可视化，支持自定义时间范围。'
    parameters = [{
        'name': 'ts_code',
        'type': 'string',
        'description': '股票代码，必填',
        'required': True
    }, {
        'name': 'start_date',
        'type': 'string',
        'description': '分析起始日期，格式YYYY-MM-DD，选填',
        'required': False
    }, {
        'name': 'end_date',
        'type': 'string',
        'description': '分析结束日期，格式YYYY-MM-DD，选填',
        'required': False
    }]
    
    def call(self, params: str, **kwargs) -> str:
        logger.info(f"ProphetAnalysisTool开始执行 - 参数: {params}")
        
        # 获取状态回调函数
        status_callback = kwargs.get('status_callback')
        
        # 发送工具开始状态
        if status_callback:
            try:
                status_callback({
                    'type': 'tool_start',
                    'message': f'正在进行Prophet周期性分析，请稍候...',
                    'tool_name': 'ProphetAnalysisTool'
                })
            except Exception as e:
                logger.warning(f'Prophet工具状态回调失败: {e}')
        
        try:
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
            engine.dispose()
            
            if len(df) < 30:
                return '历史数据不足，无法进行Prophet周期性分析。'
            
            df['ds'] = pd.to_datetime(df['trade_date'])
            df['y'] = pd.to_numeric(df['close'], errors='coerce')
            df = df.dropna(subset=['y'])
            
            # Prophet建模
            m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
            m.fit(df[['ds', 'y']])
            future = m.make_future_dataframe(periods=0)
            forecast = m.predict(future)
            
            # 保存分解图
            save_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'prophet_{ts_code}_{int(time.time()*1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            fig = m.plot_components(forecast)
            fig.savefig(save_path)
            plt.close(fig)
            
            img_url = f'/flask/static/images/{filename}'
            img_md = f'![Prophet周期分解]({img_url})'
            
            result = f"Prophet周期性分解（趋势、周、年）：\n\n{img_md}"
            
            # 发送工具完成状态
            if status_callback:
                try:
                    status_callback({
                        'type': 'success',
                        'message': f'Prophet周期性分析完成',
                        'tool_name': 'ProphetAnalysisTool',
                        'result': result
                    })
                except Exception as e:
                    logger.warning(f'Prophet工具完成状态回调失败: {e}')
            
            return result
            
        except Exception as e:
            logger.error(f"Prophet建模或分解出错: {str(e)}")
            error_msg = f'Prophet建模或分解出错: {str(e)}'
            
            # 发送工具错误状态
            if status_callback:
                try:
                    status_callback({
                        'type': 'error',
                        'message': f'Prophet周期性分析失败: {str(e)}',
                        'tool_name': 'ProphetAnalysisTool'
                    })
                except Exception as e:
                    logger.warning(f'Prophet工具错误状态回调失败: {e}')
            
            return error_msg



class ChatBIAgent(BaseAgent):
    """股票数据分析助手Agent"""
    
    def __init__(self, agent_id: str, user_id: str):
        super().__init__(agent_id, user_id)
        self.tools = {
            'stock_sql': StockSQLTool(),
            'arima_stock': ArimaStockTool(),
            'boll_detection': BollDetectionTool(),
            'prophet_analysis': ProphetAnalysisTool()
        }
    
    def get_agent_name(self) -> str:
        """重写Agent名称"""
        return '股票分析助手'
    
    def get_agent_description(self) -> str:
        """重写Agent描述"""
        return '专业的股票数据分析助手🐟，【数据均来自于网络公开数据】专注于中国股票分析，擅长SQL查询、数据可视化、股票预测和技术分析！'
    
    def get_system_prompt(self) -> str:
        return """嗨！我是你的专业股票数据分析助手小鱼🐟，【数据均来自于网络公开数据】专注于中国股票分析的强大功能！📊

**我的专业能力：**
• 📈 **SQL数据查询**：复杂的股票数据库查询，多维度分析（stock_sql工具）
• 📊 **数据可视化**：柱状图、折线图、散点图等专业图表
• 📉 **股票分析**：ARIMA预测、布林带检测、Prophet周期分析
• 🚀 **趋势预测**：基于历史数据的股价趋势分析和未来预测（arima_stock工具）
• 📋 **技术分析**：专业的股票技术指标分析报告（boll_detection、prophet_analysis工具）

**数据库支持：**

📈 **股票数据库(stock_price)**：中国股票历史价格数据（2020-2025年）
**可用股票列表：**
- 贵州茅台 (600519.SH) - 1,320条记录
- 五粮液 (000858.SZ) - 1,320条记录  
- 国泰君安 (601211.SH) - 1,301条记录
- 中芯国际 (688981.SH) - 1,192条记录

**数据字段：**
- stock_name: 股票名称
- ts_code: 股票代码
- trade_date: 交易日期
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价
- vol: 成交量
- amount: 成交额

**我的工作方式：**
🎯 当你提出股票分析需求时，我会：
1. 理解你的股票分析需求
2. 选择合适的分析方法和技术指标
3. 执行SQL查询或专业技术分析（默认从stock_price表查询）
4. 生成专业的可视化图表
5. 提供投资建议和技术分析报告

**重要说明：**
🔍 **默认查询表名：** 所有SQL查询都默认从 `stock_price` 表进行，无需用户指定表名。当用户询问股票数据时，直接使用 `SELECT * FROM stock_price WHERE ...` 的格式进行查询。

**使用示例：**

📈 **股票分析：**
- "查询贵州茅台(600519.SH)2024年的收盘价走势"
- "预测五粮液(000858.SZ)未来7天的收盘价"
- "检测国泰君安(601211.SH)近一年的超买超卖点"
- "分析中芯国际(688981.SH)的周期性规律"
- "比较贵州茅台和五粮液的价格表现"
- "查看所有股票的成交量排名"

**重要提示：**
每当工具返回markdown表格和图片时，我会原样输出全部内容（包括图片markdown），确保你能直接看到完整的分析结果。如果是预测未来价格，我会对价格趋势进行详细解释说明。

我会用最专业的态度帮你分析股票数据，让每个数字都变成有意义的投资参考！准备好开始股票分析之旅了吗？✨"""
    
    def get_function_list(self) -> List[str]:
        return ['stock_sql', 'arima_stock', 'boll_detection', 'prophet_analysis']