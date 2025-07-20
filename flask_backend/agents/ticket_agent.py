from .base_agent import BaseAgent
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
import pandas as pd
from sqlalchemy import create_engine
import matplotlib
# 设置非交互式后端，避免GUI相关错误
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import time
import json
import numpy as np
from typing import List
from utils.logger import logger

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 注册SQL执行工具
@register_tool('exc_sql')
class ExcSQLTool(BaseTool):
    """SQL查询工具"""
    description = '对于生成的SQL，进行SQL查询，并自动可视化'
    parameters = [{
        'name': 'sql_input',
        'type': 'string',
        'description': '生成的SQL语句',
        'required': True
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
                    'tool_name': 'ExcSQLTool'
                })
            except Exception as e:
                logger.warning(f'SQL工具状态回调失败: {e}')
        
        try:
            args = json.loads(params)
            sql_input = args['sql_input']
            database = args.get('database', 'ubr')
            
            logger.info(f"解析SQL参数成功 - 数据库: {database}, SQL长度: {len(sql_input)}")
            logger.debug(f"执行的SQL: {sql_input}")
            
            # 数据库连接配置
            engine = create_engine(
                f'mysql+mysqlconnector://student123:student321@rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com:3306/{database}?charset=utf8mb4',
                connect_args={'connect_timeout': 10}, 
                pool_size=10, 
                max_overflow=20
            )
            
            logger.info("数据库连接创建成功")
            
            try:
                logger.info("开始执行SQL查询")
                df = pd.read_sql(sql_input, engine)
                logger.info(f"SQL查询执行成功 - 返回行数: {len(df)}, 列数: {len(df.columns)}")
                
                md = df.head(10).to_markdown(index=False)
                
                # 生成图表
                save_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
                os.makedirs(save_dir, exist_ok=True)
                filename = f'chart_{int(time.time()*1000)}.png'
                save_path = os.path.join(save_dir, filename)
                
                logger.info(f"准备生成图表 - 文件名: {filename}")
                
                # 调用图表生成逻辑
                self._generate_chart(df, save_path)
                logger.info(f"图表生成成功 - 路径: {save_path}")
                
                img_url = f'/flask/static/images/{filename}'
                img_md = f'![图表]({img_url})'
                
                logger.info(f"SQL工具执行完成 - 数据行数: {len(df)}, 列: {list(df.columns)}")
                
                # 发送工具完成状态
                if status_callback:
                    try:
                        status_callback({
                            'type': 'success',
                            'message': f'SQL查询和数据可视化完成，返回{len(df)}行数据',
                            'tool_name': 'ExcSQLTool',
                            'result': f"{md}\n\n{img_md}"
                        })
                    except Exception as e:
                        logger.warning(f'SQL工具完成状态回调失败: {e}')
                
                return f"{md}\n\n{img_md}"
                
            except Exception as e:
                logger.error(f"SQL执行错误: {str(e)}")
                
                # 发送工具错误状态
                if status_callback:
                    try:
                        status_callback({
                            'type': 'error',
                            'message': f'SQL执行出错: {str(e)}',
                            'tool_name': 'ExcSQLTool'
                        })
                    except Exception as cb_e:
                        logger.warning(f'SQL工具错误状态回调失败: {cb_e}')
                
                return f"SQL执行出错: {str(e)}"
            finally:
                engine.dispose()
                logger.info("数据库连接已关闭")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON参数解析失败: {str(e)}")
            
            # 发送工具错误状态
            if status_callback:
                try:
                    status_callback({
                        'type': 'error',
                        'message': f'参数解析错误: {str(e)}',
                        'tool_name': 'ExcSQLTool'
                    })
                except Exception as cb_e:
                    logger.warning(f'SQL工具错误状态回调失败: {cb_e}')
            
            return f"参数解析错误: {str(e)}"
        except Exception as e:
            logger.error(f"ExcSQLTool执行异常: {str(e)}")
            
            # 发送工具错误状态
            if status_callback:
                try:
                    status_callback({
                        'type': 'error',
                        'message': f'工具执行错误: {str(e)}',
                        'tool_name': 'ExcSQLTool'
                    })
                except Exception as cb_e:
                    logger.warning(f'SQL工具错误状态回调失败: {cb_e}')
            
            return f"工具执行错误: {str(e)}"
    
    def _generate_chart(self, df, save_path):
        """生成图表的具体实现"""
        columns = df.columns
        x = np.arange(len(df))
        
        # 获取object类型列
        object_columns = df.select_dtypes(include='O').columns.tolist()
        if len(columns) > 0 and columns[0] in object_columns:
            object_columns.remove(columns[0])
        
        num_columns = df.select_dtypes(exclude='O').columns.tolist()
        
        plt.figure(figsize=(10, 6))
        
        if len(object_columns) > 0:
            # 对数据进行透视，创建堆积柱状图
            pivot_df = df.pivot_table(
                index=columns[0], 
                columns=object_columns, 
                values=num_columns, 
                fill_value=0
            )
            
            # 绘制堆积柱状图
            bottoms = None
            for col in pivot_df.columns:
                plt.bar(pivot_df.index, pivot_df[col], bottom=bottoms, label=str(col))
                if bottoms is None:
                    bottoms = pivot_df[col].copy()
                else:
                    bottoms += pivot_df[col]
        else:
            # 简单柱状图
            bottom = np.zeros(len(df))
            for column in columns[1:]:
                plt.bar(x, df[column], bottom=bottom, label=column)
                bottom += df[column]
            plt.xticks(x, df[columns[0]])
        
        plt.legend()
        plt.title("销售统计")
        plt.xlabel(columns[0] if len(columns) > 0 else "")
        plt.ylabel("门票数量")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()

class TicketAgent(BaseAgent):
    """门票助手Agent"""
    
    def get_agent_name(self) -> str:
        """重写Agent名称"""
        return '门票助手'
    
    def get_agent_description(self) -> str:
        """重写Agent描述"""
        return '门票查询与订单分析，具备SQL查询、数据可视化及多种MCP工具能力'
    
    def get_system_prompt(self) -> str:
        return """我是门票助手，专门处理门票订单相关的查询和分析。我具备以下能力：

**专业数据分析能力：**
我可以对门票订单表进行SQL查询和数据分析，以下是门票订单表的字段结构：

-- 门票订单表
CREATE TABLE `tkt_orders` ( 
   `order_time` datetime DEFAULT NULL COMMENT '订单时间', 
   `account_id` bigint DEFAULT NULL COMMENT '账户ID', 
   `gov_id` text COMMENT '身份证号', 
   `gender` text COMMENT '性别', 
   `age` double DEFAULT NULL COMMENT '年龄', 
   `province` text COMMENT '省份', 
   `SKU` text COMMENT '商品SKU', 
   `product_serial_no` text COMMENT '产品序列号', 
   `eco_main_order_id` text COMMENT '主订单ID', 
   `sales_channel` text COMMENT '销售渠道', 
   `status` text COMMENT '订单状态', 
   `order_value` double DEFAULT NULL COMMENT '订单金额', 
   `quantity` bigint DEFAULT NULL COMMENT '数量' 
 ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

**增强工具能力（自动调用）：**
1. **SQL查询工具**：执行SQL查询并自动生成可视化图表
2. **高德地图工具**：查询景点位置、路线规划（当用户询问门票相关景点位置时）
3. **网页获取工具**：获取景点官网信息、门票政策等
4. **必应搜索工具**：搜索最新的门票价格、优惠信息
5. **12306工具**：查询到达景点的火车信息
6. **Tavily搜索工具**：深度搜索景点相关信息
7. **时间工具**：处理订单时间分析、营业时间查询

**使用原则：**
- 当用户询问门票数据分析时，我会使用SQL查询工具
- 当用户询问景点位置、交通路线时，我会使用高德地图工具
- 当用户需要最新门票信息时，我会使用搜索工具
- 当用户询问交通信息时，我会使用12306工具
- 我会根据问题自动选择最合适的工具组合

**重要提示：**
每当 exc_sql 工具返回 markdown 表格和图片时，我必须原样输出工具返回的全部内容（包括图片 markdown），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。

我将以专业的态度为用户提供准确的门票数据分析和相关服务。"""
    
    def get_function_list(self) -> List[str]:
        return ['exc_sql']