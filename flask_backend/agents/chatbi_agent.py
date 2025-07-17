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

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 注册ChatBI SQL执行工具
@register_tool('chatbi_sql')
class ChatBISQLTool(BaseTool):
    """ChatBI SQL查询工具"""
    description = '执行商业智能SQL查询，生成专业的数据分析报告和可视化图表'
    parameters = [{
        'name': 'sql_input',
        'type': 'string',
        'description': '生成的SQL语句',
        'required': True
    }, {
        'name': 'chart_type',
        'type': 'string',
        'description': '图表类型：bar(柱状图)、line(折线图)、pie(饼图)、scatter(散点图)、heatmap(热力图)',
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        logger.info(f"ChatBISQLTool开始执行 - 参数: {params[:200]}...")
        
        try:
            args = json.loads(params)
            sql_input = args['sql_input']
            chart_type = args.get('chart_type', 'auto')
            database = args.get('database', 'ubr')
            
            logger.info(f"解析SQL参数成功 - 数据库: {database}, 图表类型: {chart_type}")
            
            # 数据库连接配置
            engine = create_engine(
                f'mysql+mysqlconnector://student123:student321@rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com:3306/{database}?charset=utf8mb4',
                connect_args={'connect_timeout': 10}, 
                pool_size=10, 
                max_overflow=20
            )
            
            try:
                df = pd.read_sql(sql_input, engine)
                logger.info(f"SQL查询执行成功 - 返回行数: {len(df)}, 列数: {len(df.columns)}")
                
                # 生成数据分析报告
                analysis_report = self._generate_analysis_report(df)
                
                # 生成表格
                md_table = df.head(20).to_markdown(index=False)
                
                # 生成图表
                save_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
                os.makedirs(save_dir, exist_ok=True)
                filename = f'chatbi_chart_{int(time.time()*1000)}.png'
                save_path = os.path.join(save_dir, filename)
                
                self._generate_advanced_chart(df, save_path, chart_type)
                
                img_url = f'/static/images/{filename}'
                img_md = f'![ChatBI数据分析图表]({img_url})'
                
                return f"## 📊 ChatBI数据分析报告\n\n{analysis_report}\n\n## 📈 数据详情\n\n{md_table}\n\n## 📊 可视化图表\n\n{img_md}"
                
            except Exception as e:
                logger.error(f"SQL执行错误: {str(e)}")
                return f"SQL执行出错: {str(e)}"
            finally:
                engine.dispose()
                
        except Exception as e:
            logger.error(f"ChatBISQLTool执行异常: {str(e)}")
            return f"工具执行错误: {str(e)}"
    
    def _generate_analysis_report(self, df):
        """生成数据分析报告"""
        try:
            report = []
            report.append(f"**数据概览：** 共 {len(df)} 行数据，{len(df.columns)} 个字段")
            
            # 数值型字段统计
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                report.append("\n**数值字段统计：**")
                for col in numeric_cols:
                    stats = df[col].describe()
                    report.append(f"- {col}: 平均值 {stats['mean']:.2f}, 最大值 {stats['max']:.2f}, 最小值 {stats['min']:.2f}")
            
            # 分类字段统计
            categorical_cols = df.select_dtypes(include=['object']).columns
            if len(categorical_cols) > 0:
                report.append("\n**分类字段统计：**")
                for col in categorical_cols[:3]:  # 只显示前3个分类字段
                    unique_count = df[col].nunique()
                    report.append(f"- {col}: {unique_count} 个不同值")
            
            return "\n".join(report)
        except Exception as e:
            return f"数据分析报告生成失败: {str(e)}"
    
    def _generate_advanced_chart(self, df, save_path, chart_type):
        """生成高级图表"""
        plt.figure(figsize=(12, 8))
        
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            categorical_cols = df.select_dtypes(include=['object']).columns
            
            if chart_type == 'auto' or chart_type == 'bar':
                if len(categorical_cols) > 0 and len(numeric_cols) > 0:
                    # 柱状图
                    x_col = categorical_cols[0]
                    y_col = numeric_cols[0]
                    
                    # 聚合数据
                    agg_df = df.groupby(x_col)[y_col].sum().sort_values(ascending=False).head(10)
                    
                    plt.bar(range(len(agg_df)), agg_df.values, color='skyblue')
                    plt.xticks(range(len(agg_df)), agg_df.index, rotation=45)
                    plt.title(f'{y_col} 按 {x_col} 分布', fontsize=16)
                    plt.ylabel(y_col)
                    plt.xlabel(x_col)
                    
            elif chart_type == 'pie' and len(categorical_cols) > 0:
                # 饼图
                col = categorical_cols[0]
                value_counts = df[col].value_counts().head(8)
                plt.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%')
                plt.title(f'{col} 分布', fontsize=16)
                
            elif chart_type == 'line' and len(numeric_cols) >= 2:
                # 折线图
                x_col = numeric_cols[0]
                y_col = numeric_cols[1]
                plt.plot(df[x_col], df[y_col], marker='o')
                plt.title(f'{y_col} vs {x_col}', fontsize=16)
                plt.xlabel(x_col)
                plt.ylabel(y_col)
                
            elif chart_type == 'scatter' and len(numeric_cols) >= 2:
                # 散点图
                x_col = numeric_cols[0]
                y_col = numeric_cols[1]
                plt.scatter(df[x_col], df[y_col], alpha=0.6)
                plt.title(f'{y_col} vs {x_col} 散点图', fontsize=16)
                plt.xlabel(x_col)
                plt.ylabel(y_col)
                
            else:
                # 默认柱状图
                if len(numeric_cols) > 0:
                    col = numeric_cols[0]
                    plt.hist(df[col], bins=20, alpha=0.7, color='lightblue')
                    plt.title(f'{col} 分布直方图', fontsize=16)
                    plt.xlabel(col)
                    plt.ylabel('频次')
            
            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.error(f"图表生成失败: {str(e)}")
            # 生成简单的默认图表
            plt.text(0.5, 0.5, f'图表生成失败\n{str(e)}', ha='center', va='center', transform=plt.gca().transAxes)
            plt.savefig(save_path)
            plt.close()

class ChatBIAgent(BaseAgent):
    """ChatBI商业智能助手Agent"""
    
    def get_agent_name(self) -> str:
        """重写Agent名称"""
        return 'ChatBI助手'
    
    def get_agent_description(self) -> str:
        """重写Agent描述"""
        return '专业的商业智能数据分析师🐟，擅长SQL查询、数据可视化、商业洞察分析，让数据说话！'
    
    def get_system_prompt(self) -> str:
        return """嗨！我是你的专业ChatBI商业智能助手小鱼🐟，专门帮你进行数据分析和商业洞察！📊

**我的专业能力：**
• 📈 **SQL数据查询**：复杂的数据库查询，多表关联分析
• 📊 **数据可视化**：柱状图、折线图、饼图、散点图、热力图等
• 🔍 **商业洞察**：从数据中发现商业价值和趋势
• 📋 **报表生成**：专业的数据分析报告
• 🎯 **KPI分析**：关键指标监控和分析
• 📉 **趋势预测**：基于历史数据的趋势分析

**数据库表结构：**
我可以访问门票订单数据库，包含以下字段：
- order_time: 订单时间
- account_id: 账户ID  
- gender: 性别
- age: 年龄
- province: 省份
- SKU: 商品SKU
- sales_channel: 销售渠道
- status: 订单状态
- order_value: 订单金额
- quantity: 数量

**我的工作方式：**
🎯 当你提出数据分析需求时，我会：
1. 理解你的业务问题
2. 设计合适的SQL查询
3. 执行数据分析
4. 生成专业的可视化图表
5. 提供商业洞察和建议

**使用示例：**
- "分析各省份的销售情况"
- "查看最近一个月的订单趋势"
- "分析不同年龄段的消费偏好"
- "各销售渠道的效果对比"

我会用最专业的态度帮你挖掘数据价值，让每个数字都变成有意义的商业洞察！准备好开始数据探索之旅了吗？✨"""
    
    def get_function_list(self) -> List[str]:
        return ['chatbi_sql']