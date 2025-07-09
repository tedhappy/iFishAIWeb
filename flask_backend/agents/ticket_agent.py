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
                
                img_url = f'/static/images/{filename}'
                img_md = f'![图表]({img_url})'
                
                logger.info(f"SQL工具执行完成 - 数据行数: {len(df)}, 列: {list(df.columns)}")
                return f"{md}\n\n{img_md}"
                
            except Exception as e:
                logger.error(f"SQL执行错误: {str(e)}")
                return f"SQL执行出错: {str(e)}"
            finally:
                engine.dispose()
                logger.info("数据库连接已关闭")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON参数解析失败: {str(e)}")
            return f"参数解析错误: {str(e)}"
        except Exception as e:
            logger.error(f"ExcSQLTool执行异常: {str(e)}")
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
    
    def _init_agent(self) -> Assistant:
        llm_cfg = {
            'model': 'qwen-turbo-latest',
            'timeout': 30,
            'retry_count': 3,
        }
        
        return Assistant(
            llm=llm_cfg,
            name='门票助手',
            description='门票查询与订单分析',
            system_message=self.get_system_prompt(),
            function_list=self.get_function_list()
        )
    
    def get_system_prompt(self) -> str:
        return """我是门票助手，以下是关于门票订单表相关的字段，我可能会编写对应的SQL，对数据进行查询
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

我将回答用户关于门票相关的问题。

每当 exc_sql 工具返回 markdown 表格和图片时，你必须原样输出工具返回的全部内容（包括图片 markdown），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。"""
    
    def get_function_list(self) -> List[str]:
        return ['exc_sql']