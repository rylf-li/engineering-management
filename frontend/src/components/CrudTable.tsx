import React, { useState, useEffect, useCallback, useMemo } from 'react';
import dayjs from 'dayjs';
import {
  Table,
  Button,
  Space,
  Input,
  Modal,
  Form,
  Popconfirm,
  Upload,
  message,
  Card,
  Typography,
  Row,
  Col,
  Select,
  InputNumber,
  DatePicker,
  Descriptions,
  Drawer,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  DownloadOutlined,
  UploadOutlined,
  EditOutlined,
  HolderOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import api from '../utils/api';
import * as XLSX from 'xlsx';

const { Title } = Typography;

// ─── Type Definitions ────────────────────────────────────────────────────────

export interface BatchAction {
  key: string;
  label: string;
  icon?: React.ReactNode;
  type?: 'primary' | 'default' | 'danger';
  handler: (selectedRowKeys: React.Key[], selectedRows: any[]) => void;
  /** 可选条件控制显示 */
  showWhen?: (selectedRows: any[]) => boolean;
}

export interface SubTableConfig {
  /** 子表API基础路径，如 /api/projects/{parentId}/contracts 或 /api/projects/1/contracts */
  endpoint: string;
  columns: any[];
  title: string;
  rowKey?: string;
  /** 父表关联字段（用于 query 参数） */
  parentField?: string;
  /** 父记录ID（静态传入，或动态从行记录获取） */
  parentId?: number | string;
  /** 自定义表单内容 */
  formFields?: React.ReactNode;
  /** 批量操作按钮（子表自己的额外批量操作） */
  batchActions?: BatchAction[];
  /** 是否启用拖拽排序（子表默认关闭） */
  draggable?: boolean;
  /** 是否显示搜索 */
  searchable?: boolean;
  /** 是否显示导入导出 */
  importable?: boolean;
  exportable?: boolean;
  /** 初始表单值 */
  initialValues?: Record<string, any>;
}

export interface FilterConfig {
  field: string;
  label: string;
  options: { label: string; value: string }[];
  placeholder?: string;
  /** 默认值（空字符串表示不筛选） */
  defaultValue?: string;
}

export interface CrudTableProps {
  apiEndpoint: string;
  columns: any[];
  title: string;

  // ── 向后兼容: 旧版子表 ──
  /** @deprecated 请使用 subTable 代替 */
  subTableTitle?: string;
  /** @deprecated 请使用 subTable 代替 */
  subTableColumns?: any[];
  /** @deprecated 请使用 subTable 代替 */
  subTableEndpoint?: string;

  // ── 新版子表配置 ──
  subTable?: SubTableConfig;

  // ── 自定义扩展行（覆盖默认子表，支持多子表/Tabs等复杂场景） ──
  expandedRowRender?: (record: any) => React.ReactNode;

  // ── 表单配置 ──
  formFields?: React.ReactNode;
  initialValues?: Record<string, any>;
  rowKey?: string;

  // ── 批量操作 ──
  batchActions?: BatchAction[];

  // ── 功能开关 ──
  draggable?: boolean;
  searchable?: boolean;
  importable?: boolean;
  exportable?: boolean;

  // ── 状态选项（用于批量状态编辑） ──
  statusOptions?: { label: string; value: string }[];
  /** 状态字段名 */
  statusField?: string;
  /** 自定义详情渲染（启用详情按钮） */
  detailRender?: (record: any) => React.ReactNode;
  /** 数据变更回调（用于父组件刷新摘要等） */
  onDataChange?: () => void;
  /** 筛选配置列表 */
  filters?: FilterConfig[];
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** 从列定义生成详情视图 */
export const renderDetail = (record: any, columns: any[]): React.ReactNode => {
  const filtered = columns.filter((col: any) => col.dataIndex && col.key !== 'action');
  return (
    <Descriptions column={1} bordered size="small">
      {filtered.map((col: any) => {
        let val = record[col.dataIndex];
        return (
          <Descriptions.Item key={col.dataIndex} label={col.title as string}>
            {col.render ? col.render(val, record) : (val ?? '-')}
          </Descriptions.Item>
        );
      })}
    </Descriptions>
  );
};

/** 解析后端返回数据，格式统一为 {items, total} */
const parseResponse = (res: any): { items: any[]; total: number } => {
  if (Array.isArray(res)) return { items: res, total: res.length };
  if (res.data) return { items: res.data?.items ?? res.data?.results ?? [], total: res.data?.total ?? res.data?.items?.length ?? 0 };
  return { items: res?.items ?? res?.results ?? [], total: res?.total ?? res?.items?.length ?? 0 };
};

/** 判断columns中是否包含某个特定key */
const columnExists = (cols: any[], key: string): boolean =>
  cols.some((c) => c.key === key);

// ─── Draggable Row ───────────────────────────────────────────────────────────

interface DraggableRowProps {
  id: React.Key;
  children: React.ReactNode;
  style?: React.CSSProperties;
  [key: string]: any;
}

const DraggableRow = React.forwardRef<HTMLTableRowElement, DraggableRowProps>(
  ({ id, children, style, ...props }, ref) => {
    const {
      attributes,
      listeners,
      setNodeRef,
      transform,
      transition,
      isDragging,
    } = useSortable({ id });

    const draggableStyle: React.CSSProperties = {
      ...style,
      transform: CSS.Transform.toString(transform),
      transition,
      opacity: isDragging ? 0.5 : 1,
      cursor: isDragging ? 'grabbing' : undefined,
    };

    return (
      <tr
        {...props}
        ref={setNodeRef}
        style={draggableStyle}
        {...attributes}
      >
        {React.Children.map(children, (child, index) => {
          if (index === 0) {
            // Inject drag handle listeners into the first cell (drag handle column)
            return React.cloneElement(child as React.ReactElement, {
              children: (
                <span
                  {...listeners}
                  style={{
                    cursor: 'grab',
                    touchAction: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                  }}
                >
                  {(child as React.ReactElement)?.props?.children}
                </span>
              ),
            });
          }
          return child;
        })}
      </tr>
    );
  }
);

DraggableRow.displayName = 'DraggableRow';

// ─── Mini CrudTable (Sub-Table) ──────────────────────────────────────────────
export interface MiniCrudTableProps {
  /** 子表API基础路径 */
  endpoint: string;
  columns: any[];
  title: string;
  rowKey?: string;
  formFields?: React.ReactNode;
  batchActions?: BatchAction[];
  draggable?: boolean;
  searchable?: boolean;
  importable?: boolean;
  exportable?: boolean;
  initialValues?: Record<string, any>;
  statusOptions?: { label: string; value: string }[];
  statusField?: string;
  /** 自定义详情渲染（启用详情按钮） */
  detailRender?: (record: any) => React.ReactNode;
  /** 筛选配置列表 */
  filters?: FilterConfig[];
}

export const MiniCrudTable: React.FC<MiniCrudTableProps> = ({
  endpoint,
  columns,
  title,
  rowKey = 'id',
  formFields,
  initialValues = {},
  batchActions: extraBatchActions,
  searchable = true,
  importable = false,
  exportable = false,
  statusOptions,
  statusField = 'status',
  draggable = false,
  detailRender,
  filters: filterConfigs,
}) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<string>('asc');
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [form] = Form.useForm();

  const fetchData = useCallback(
    async (page = 1, pageSize = 10, sort_field = '', sort_order = 'asc') => {
      setLoading(true);
      try {
        const params: any = { page, page_size: pageSize };
        if (searchText) params.search = searchText;
        if (sort_field) { params.sort_field = sort_field; params.sort_order = sort_order; }
        // Add filter params
        if (filterConfigs) {
          filterConfigs.forEach((fc) => {
            const val = filterValues[fc.field];
            if (val && val !== fc.defaultValue) {
              params[fc.field] = val;
            }
          });
        }
        const res = await api.get(endpoint, { params });
        const { items, total } = parseResponse(res);
        setData(items);
        setPagination((prev) => ({ ...prev, current: page, total }));
      } catch (err: any) {
        message.error(err.message || '获取数据失败');
        setData([]);
      } finally {
        setLoading(false);
      }
    },
    [endpoint, searchText, filterConfigs, filterValues]
  );

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAdd = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue(initialValues);
    setModalVisible(true);
  };

  // ── MiniCrudTable handleEdit ──
  const handleEdit = (record: any) => {
    setEditingRecord(record);
    // Convert date strings to dayjs objects for DatePicker fields
    const formValues: any = { ...record };
    columns.forEach((col: any) => {
      const val = formValues[col.dataIndex];
      if (val && typeof val === 'string' && (
        col.dataIndex?.toLowerCase().includes('date') ||
        col.dataIndex?.toLowerCase().includes('time')
      )) {
        formValues[col.dataIndex] = dayjs(val.split('T')[0] || val);
      }
    });
    form.setFieldsValue(formValues);
    setModalVisible(true);
  };

  const handleDelete = async (id: number | string) => {
    try {
      await api.delete(`${endpoint}/${id}`);
      message.success('删除成功');
      fetchData(pagination.current, pagination.pageSize);
    } catch (err: any) {
      message.error(err.message || '删除失败');
    }
  };

  const handleBatchDelete = async () => {
    Modal.confirm({
      title: `确认删除选中的 ${selectedRowKeys.length} 项？`,
      content: '删除后数据不可恢复',
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.post(`${endpoint}/batch-delete/`, { ids: selectedRowKeys });
          message.success('批量删除成功');
          setSelectedRowKeys([]);
          fetchData(pagination.current, pagination.pageSize);
        } catch (err: any) {
          message.error(err.message || '批量删除失败');
        }
      },
    });
  };

  const handleBatchStatus = (value: string) => {
    if (!value) return;
    Modal.confirm({
      title: `确认将选中的 ${selectedRowKeys.length} 项状态改为「${value}」？`,
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.post(`${endpoint}/batch-status/`, {
            ids: selectedRowKeys,
            field: statusField,
            value,
          });
          message.success('批量状态更新成功');
          setSelectedRowKeys([]);
          fetchData(pagination.current, pagination.pageSize);
        } catch (err: any) {
          message.error(err.message || '批量状态更新失败');
        }
      },
    });
  };

  const handleTableChange = useCallback(
    (pag: any, _filters: any, sorter: any) => {
      let sf = '';
      let so = 'asc';
      if (sorter && sorter.field) {
        sf = sorter.field as string;
        so = sorter.order === 'descend' ? 'desc' : 'asc';
      }
      setSortField(sf);
      setSortOrder(so);
      fetchData(pag.current, pag.pageSize, sf, so);
    },
    [fetchData]
  );

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      // Convert dayjs objects to date strings for API
      const apiValues: any = {};
      Object.entries(values).forEach(([key, val]) => {
        if (val && typeof val === 'object' && val._isAMomentObject === undefined && dayjs.isDayjs(val)) {
          apiValues[key] = val.format('YYYY-MM-DD');
        } else {
          apiValues[key] = val;
        }
      });
      if (editingRecord) {
        await api.put(`${endpoint}/${editingRecord[rowKey]}`, apiValues);
        message.success('更新成功');
      } else {
        await api.post(endpoint, apiValues);
        message.success('创建成功');
      }
      setModalVisible(false);
      form.resetFields();
      fetchData(pagination.current, pagination.pageSize);
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err.message || '操作失败');
    }
  };

  // Build columns
  const [detailRecord, setDetailRecord] = useState<any>(null);

  const actionColumn = {
    title: '操作',
    key: 'action',
    width: detailRender ? 200 : 160,
    render: (_: any, record: any) => (
      <Space>
        {detailRender && (
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => setDetailRecord(record)}>
            详情
          </Button>
        )}
        <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
          编辑
        </Button>
        <Popconfirm title="确认删除该记录？" onConfirm={() => handleDelete(record[rowKey])}>
          <Button type="link" size="small" danger>
            删除
          </Button>
        </Popconfirm>
      </Space>
    ),
  };

  const tableColumns = useMemo(() => {
    const cols = [...columns];
    // 自动为有 dataIndex 的列添加 sorter 属性
    cols.forEach((col: any) => {
      if (col.dataIndex && col.key !== 'action' && !col.sorter) {
        col.sorter = true;
      }
    });
    if (!columnExists(cols, 'action')) {
      cols.push(actionColumn);
    }
    return cols;
  }, [columns]);

  // Auto-generate form items
  const renderFormItems = () => {
    if (formFields) return formFields;
    return columns
      .filter((col: any) => col.dataIndex && col.key !== 'action')
      .map((col: any) => {
        const dataIndex = col.dataIndex as string;
        const label = (col.title as string) || dataIndex;
        const isNumber = dataIndex.toLowerCase().includes('amount') ||
          dataIndex.toLowerCase().includes('price') ||
          dataIndex.toLowerCase().includes('salary') ||
          dataIndex.toLowerCase().includes('budget') ||
          dataIndex.toLowerCase().includes('money');

        const isDate = dataIndex.toLowerCase().includes('date') ||
          dataIndex.toLowerCase().includes('time') ||
          dataIndex === 'created_at' ||
          dataIndex === 'updated_at';

        return (
          <Form.Item
            key={dataIndex}
            name={dataIndex}
            label={label}
            rules={[{ required: !col.optional, message: `请输入${label}` }]}
          >
            {isNumber ? (
              <InputNumber style={{ width: '100%' }} prefix="¥" />
            ) : isDate ? (
              <DatePicker style={{ width: '100%' }} />
            ) : (
              <Input placeholder={`请输入${label}`} />
            )}
          </Form.Item>
        );
      });
  };

  return (
    <div>
      {/* Toolbar */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Space wrap>
            {searchable && (
              <Input.Search
                placeholder="搜索..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onSearch={() => fetchData()}
                style={{ width: 180 }}
                allowClear
              />
            )}
            {filterConfigs?.map((fc) => (
              <Select
                key={fc.field}
                size="small"
                placeholder={fc.placeholder || `选择${fc.label}`}
                style={{ width: 130 }}
                allowClear
                value={filterValues[fc.field] || undefined}
                onChange={(val) => {
                  setFilterValues((prev) => ({ ...prev, [fc.field]: val || '' }));
                  fetchData(1, pagination.pageSize, sortField, sortOrder);
                }}
              >
                {fc.options.map((opt) => (
                  <Select.Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Select.Option>
                ))}
              </Select>
            ))}
            <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleAdd}>
              新增
            </Button>
            {selectedRowKeys.length > 0 && (
              <>
                <Popconfirm
                  title={`确认删除选中的 ${selectedRowKeys.length} 项？`}
                  onConfirm={handleBatchDelete}
                >
                  <Button size="small" danger icon={<DeleteOutlined />}>
                    批量删除 ({selectedRowKeys.length})
                  </Button>
                </Popconfirm>
                {statusOptions && statusOptions.length > 0 && (
                  <Select
                    placeholder="批量修改状态"
                    style={{ width: 140 }}
                    size="small"
                    onChange={handleBatchStatus}
                    allowClear
                  >
                    {statusOptions.map((opt) => (
                      <Select.Option key={opt.value} value={opt.value}>
                        {opt.label}
                      </Select.Option>
                    ))}
                  </Select>
                )}
                {extraBatchActions?.map((action) => {
                  if (action.showWhen && !action.showWhen(data.filter((_, i) => selectedRowKeys.includes(data[i]?.[rowKey])))) {
                    return null;
                  }
                  const selectedRows = data.filter((d) => selectedRowKeys.includes(d[rowKey]));
                  return (
                    <Button
                      key={action.key}
                      size="small"
                      type={(action.type === 'danger' ? 'default' : action.type) as any || 'default'}
                      icon={action.icon}
                      onClick={() => action.handler(selectedRowKeys, selectedRows)}
                    >
                      {action.label}
                    </Button>
                  );
                })}
              </>
            )}
            {importable && (
              <Upload
                accept=".xlsx,.xls,.csv"
                showUploadList={false}
                beforeUpload={handleImportExcel}
              >
                <Button size="small" icon={<UploadOutlined />}>导入Excel</Button>
              </Upload>
            )}
            {exportable && (
              <Button size="small" icon={<DownloadOutlined />} onClick={handleExportCSV}>
                导出CSV
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      {/* Table */}
      <Table
        rowKey={rowKey}
        columns={tableColumns}
        dataSource={data}
        loading={loading}
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => fetchData(page, pageSize, sortField, sortOrder),
        }}
        onChange={handleTableChange}
        scroll={{ x: 'max-content' }}
        size="small"
      />

      {/* Modal */}
      <Modal
        title={editingRecord ? '编辑' : '新增'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        destroyOnClose
        width={640}
      >
        <Form form={form} layout="vertical">
          {renderFormItems()}
        </Form>
      </Modal>

      {/* Detail Drawer — combines record info + sub-tables */}
      {detailRender && detailRecord && (
        <Drawer
          title={`${title} - 详情`}
          open={!!detailRecord}
          onClose={() => setDetailRecord(null)}
          width={960}
          styles={{ body: { padding: 16 } }}
        >
          {detailRender(detailRecord)}
        </Drawer>
      )}
    </div>
  );
};

// ─── Main CrudTable ──────────────────────────────────────────────────────────

const CrudTable: React.FC<CrudTableProps> = ({
  apiEndpoint,
  columns,
  title,
  // 旧版子表 (向后兼容)
  subTableTitle: legacySubTableTitle,
  subTableColumns: legacySubTableColumns,
  subTableEndpoint: legacySubTableEndpoint,
  // 新版子表
  subTable,
  // 表单
  formFields,
  initialValues = {},
  rowKey = 'id',
  // 批量操作
  batchActions,
  // 功能开关
  draggable = true,
  searchable = true,
  importable = true,
  exportable = true,
  statusOptions,
  statusField = 'status',
  expandedRowRender: customExpandedRowRender,
  detailRender,
  onDataChange,
  filters: filterConfigs,
}) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [expandedRowKeys, setExpandedRowKeys] = useState<React.Key[]>([]);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<string>('asc');
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [form] = Form.useForm();

  // ── Drag & Drop state ──
  const [activeId, setActiveId] = useState<React.Key | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  // ── Data Fetching ──
  const fetchData = useCallback(
    async (page = 1, pageSize = 10, sort_field = '', sort_order = 'asc') => {
      setLoading(true);
      try {
        const params: any = { page, page_size: pageSize };
        if (searchText) params.search = searchText;
        if (sort_field) { params.sort_field = sort_field; params.sort_order = sort_order; }
        // Add filter params
        if (filterConfigs) {
          filterConfigs.forEach((fc) => {
            const val = filterValues[fc.field];
            if (val && val !== fc.defaultValue) {
              params[fc.field] = val;
            }
          });
        }
        const res = await api.get(apiEndpoint, { params });
        const { items, total } = parseResponse(res);
        setData(items);
        setPagination((prev) => ({ ...prev, current: page, total }));
      } catch (err: any) {
        message.error(err.message || '获取数据失败');
        setData([]);
      } finally {
        setLoading(false);
      }
    },
    [apiEndpoint, searchText, filterConfigs, filterValues]
  );

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ── CRUD Handlers ──
  const handleAdd = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue(initialValues);
    setModalVisible(true);
  };

  // ── MiniCrudTable handleEdit ──
  const handleEdit = (record: any) => {
    setEditingRecord(record);
    // Convert date strings to dayjs objects for DatePicker fields
    const formValues: any = { ...record };
    columns.forEach((col: any) => {
      const val = formValues[col.dataIndex];
      if (val && typeof val === 'string' && (
        col.dataIndex?.toLowerCase().includes('date') ||
        col.dataIndex?.toLowerCase().includes('time')
      )) {
        formValues[col.dataIndex] = dayjs(val.split('T')[0] || val);
      }
    });
    form.setFieldsValue(formValues);
    setModalVisible(true);
  };

  const handleDelete = async (id: number | string) => {
    try {
      await api.delete(`${apiEndpoint}${id}`);
      message.success('删除成功');
      fetchData(pagination.current, pagination.pageSize);
      onDataChange?.();
    } catch (err: any) {
      message.error(err.message || '删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      // Convert dayjs objects to date strings for API
      const apiValues: any = {};
      Object.entries(values).forEach(([key, val]) => {
        if (val && typeof val === 'object' && val._isAMomentObject === undefined && dayjs.isDayjs(val)) {
          apiValues[key] = val.format('YYYY-MM-DD');
        } else {
          apiValues[key] = val;
        }
      });
      if (editingRecord) {
        await api.put(`${apiEndpoint}${editingRecord[rowKey]}`, apiValues);
        message.success('更新成功');
      } else {
        await api.post(apiEndpoint, apiValues);
        message.success('创建成功');
      }
      setModalVisible(false);
      form.resetFields();
      fetchData(pagination.current, pagination.pageSize);
      onDataChange?.();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err.message || '操作失败');
    }
  };

  // ── Batch Operations ──
  const handleBatchDelete = async () => {
    Modal.confirm({
      title: `确认删除选中的 ${selectedRowKeys.length} 项？`,
      content: '删除后数据不可恢复',
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.post(`${apiEndpoint}batch-delete/`, { ids: selectedRowKeys });
          message.success('批量删除成功');
          setSelectedRowKeys([]);
          fetchData(pagination.current, pagination.pageSize);
          onDataChange?.();
        } catch (err: any) {
          message.error(err.message || '批量删除失败');
        }
      },
    });
  };

  const handleBatchStatus = (value: string) => {
    if (!value) return;
    Modal.confirm({
      title: `确认将选中的 ${selectedRowKeys.length} 项状态改为「${value}」？`,
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.post(`${apiEndpoint}batch-status/`, {
            ids: selectedRowKeys,
            field: statusField,
            value,
          });
          message.success('批量状态更新成功');
          setSelectedRowKeys([]);
          fetchData(pagination.current, pagination.pageSize);
          onDataChange?.();
        } catch (err: any) {
          message.error(err.message || '批量状态更新失败');
        }
      },
    });
  };

  // ── Drag & Drop Handlers ──
  const handleDragStart = (event: any) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = async (event: any) => {
    setActiveId(null);
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = data.findIndex((item) => item[rowKey] === active.id);
    const newIndex = data.findIndex((item) => item[rowKey] === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    // Optimistically reorder the local data
    const newData = arrayMove(data, oldIndex, newIndex);
    setData(newData);

    try {
      // Send the new ordering (IDs in order)
      const orderedIds = newData.map((item) => item[rowKey]);
      await api.post(`${apiEndpoint}reorder`, { ids: orderedIds });
      message.success('排序已更新');
    } catch (err: any) {
      message.error(err.message || '排序更新失败，请重试');
      fetchData(pagination.current, pagination.pageSize);
    }
  };

  // ── Import / Export ──
  const handleExportCSV = () => {
    try {
      const ws = XLSX.utils.json_to_sheet(data);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
      XLSX.writeFile(wb, `${title}.csv`, { bookType: 'csv' });
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };

  const handleImportExcel = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      await api.post(`${apiEndpoint}import/excel`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      message.success('导入成功');
      fetchData();
      onDataChange?.();
    } catch (err: any) {
      message.error(err.message || '导入失败');
    }
    return false;
  };

  // ── Columns ──
  const [detailRecord, setDetailRecord] = useState<any>(null);

  const actionColumn = {
    title: '操作',
    key: 'action',
    width: detailRender ? 200 : 160,
    render: (_: any, record: any) => (
      <Space>
        {detailRender && (
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => setDetailRecord(record)}>
            详情
          </Button>
        )}
        <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
          编辑
        </Button>
        <Popconfirm title="确认删除该记录？" onConfirm={() => handleDelete(record[rowKey])}>
          <Button type="link" size="small" danger>
            删除
          </Button>
        </Popconfirm>
      </Space>
    ),
  };

  // Drag handle column (first column)
  const dragHandleColumn = draggable
    ? {
        title: '',
        key: '_drag_handle',
        width: 40,
        fixed: 'left' as const,
        render: () => <HolderOutlined style={{ color: '#999', fontSize: 16 }} />,
      }
    : null;

  // Build final column list
  const tableColumns = useMemo(() => {
    const cols: any[] = [];
    if (dragHandleColumn) cols.push(dragHandleColumn);
    // 自动为有 dataIndex 的列添加 sorter 属性
    cols.push(...columns.map((col: any) => {
      if (col.dataIndex && col.key !== 'action' && !col.sorter) {
        return { ...col, sorter: true };
      }
      return col;
    }));
    if (!columnExists(columns, 'action')) {
      cols.push(actionColumn);
    }
    return cols;
  }, [columns, draggable]);

  // ── Sub-Table Configuration (resolve old + new) ──
  const hasSubTable = !!(subTable || (legacySubTableColumns && legacySubTableEndpoint));
  // ── Custom expandedRowRender (overrides default sub-table) ──
  const hasCustomExpand = !!customExpandedRowRender;
  const willExpand = hasSubTable || hasCustomExpand;
  const effectiveExpandedRowRender = customExpandedRowRender || defaultExpandedRowRender;
  const resolvedSubTable: SubTableConfig | null = useMemo(() => {
    if (subTable) return subTable;
    if (legacySubTableColumns && legacySubTableEndpoint) {
      return {
        endpoint: legacySubTableEndpoint,
        columns: legacySubTableColumns,
        title: legacySubTableTitle || '详情',
        rowKey,
      };
    }
    return null;
  }, [subTable, legacySubTableColumns, legacySubTableEndpoint, legacySubTableTitle, rowKey]);

  // ── Expanded Row Render ──
  function defaultExpandedRowRender(record: any) {
    if (!resolvedSubTable) return null;

    // Resolve dynamic parent ID from the record
    const parentId = record[rowKey];

    // Build real endpoint with parent ID substitution
    let realEndpoint = resolvedSubTable.endpoint;
    if (realEndpoint.includes('{parentId}')) {
      realEndpoint = realEndpoint.replace(/\{parentId\}/g, String(parentId));
    }

    return (
      <Card
        title={resolvedSubTable.title}
        size="small"
        style={{ margin: 8, background: '#fafafa' }}
      >
        <MiniCrudTable
          endpoint={realEndpoint}
          columns={resolvedSubTable.columns}
          title={resolvedSubTable.title}
          rowKey={resolvedSubTable.rowKey || rowKey}
          formFields={resolvedSubTable.formFields}
          initialValues={
            resolvedSubTable.parentField
              ? { [resolvedSubTable.parentField]: parentId }
              : {}
          }
          batchActions={resolvedSubTable.batchActions}
          statusOptions={statusOptions}
          statusField={statusField}
          searchable={resolvedSubTable.searchable ?? true}
          importable={resolvedSubTable.importable ?? false}
          exportable={resolvedSubTable.exportable ?? false}
          draggable={false}
        />
      </Card>
    );
  };

  // ── Auto-generate form items ──
  const renderFormItems = () => {
    if (formFields) return formFields;
    return columns
      .filter((col: any) => col.dataIndex && col.key !== 'action' && col.key !== '_drag_handle')
      .map((col: any) => {
        const dataIndex = col.dataIndex as string;
        const label = (col.title as string) || dataIndex;
        const isNumber =
          dataIndex.toLowerCase().includes('amount') ||
          dataIndex.toLowerCase().includes('price') ||
          dataIndex.toLowerCase().includes('salary') ||
          dataIndex.toLowerCase().includes('budget') ||
          dataIndex.toLowerCase().includes('money');

        const isDate =
          dataIndex.toLowerCase().includes('date') ||
          dataIndex.toLowerCase().includes('time') ||
          dataIndex === 'created_at' ||
          dataIndex === 'updated_at';

        return (
          <Form.Item
            key={dataIndex}
            name={dataIndex}
            label={label}
            rules={[{ required: !col.optional, message: `请输入${label}` }]}
          >
            {isNumber ? (
              <InputNumber style={{ width: '100%' }} prefix="¥" />
            ) : isDate ? (
              <DatePicker style={{ width: '100%' }} />
            ) : (
              <Input placeholder={`请输入${label}`} />
            )}
          </Form.Item>
        );
      });
  };

  const handleTableChange = useCallback(
    (pag: any, _filters: any, sorter: any) => {
      let sf = '';
      let so = 'asc';
      if (sorter && sorter.field) {
        sf = sorter.field as string;
        so = sorter.order === 'descend' ? 'desc' : 'asc';
      }
      setSortField(sf);
      setSortOrder(so);
      fetchData(pag.current, pag.pageSize, sf, so);
    },
    [fetchData]
  );

  // ── Render ──
  // Custom row component for drag & drop support
  const components = draggable
    ? {
        body: {
          row: (rowProps: any) => {
            const record = rowProps['data-row-key'];
            return <DraggableRow id={record || rowProps['data-row-key']} {...rowProps} />;
          },
        },
      }
    : undefined;

  return (
    <Card>
      {/* Header / Toolbar */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            {title}
          </Title>
        </Col>
        <Col>
          <Space wrap>
            {searchable && (
              <Input.Search
                placeholder="搜索..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onSearch={() => fetchData()}
                style={{ width: 200 }}
                allowClear
              />
            )}
            {filterConfigs?.map((fc) => (
              <Select
                key={fc.field}
                placeholder={fc.placeholder || `选择${fc.label}`}
                style={{ width: 140 }}
                allowClear
                value={filterValues[fc.field] || undefined}
                onChange={(val) => {
                  setFilterValues((prev) => ({ ...prev, [fc.field]: val || '' }));
                  fetchData(1, pagination.pageSize, sortField, sortOrder);
                }}
              >
                {fc.options.map((opt) => (
                  <Select.Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Select.Option>
                ))}
              </Select>
            ))}
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              新增
            </Button>

            {selectedRowKeys.length > 0 && (
              <>
                <Popconfirm
                  title={`确认删除选中的 ${selectedRowKeys.length} 项？`}
                  onConfirm={handleBatchDelete}
                >
                  <Button danger icon={<DeleteOutlined />}>
                    批量删除 ({selectedRowKeys.length})
                  </Button>
                </Popconfirm>

                {statusOptions && statusOptions.length > 0 && (
                  <Select
                    placeholder="批量修改状态"
                    style={{ width: 150 }}
                    onChange={handleBatchStatus}
                    allowClear
                  >
                    {statusOptions.map((opt) => (
                      <Select.Option key={opt.value} value={opt.value}>
                        {opt.label}
                      </Select.Option>
                    ))}
                  </Select>
                )}

                {batchActions?.map((action) => {
                  const selectedRows = data.filter((d) =>
                    selectedRowKeys.includes(d[rowKey])
                  );
                  if (action.showWhen && !action.showWhen(selectedRows)) {
                    return null;
                  }
                  return (
                    <Button
                      key={action.key}
                      type={(action.type === 'danger' ? 'default' : action.type) as any || 'default'}
                      icon={action.icon}
                      onClick={() => action.handler(selectedRowKeys, selectedRows)}
                    >
                      {action.label}
                    </Button>
                  );
                })}
              </>
            )}

            {importable && (
              <Upload
                accept=".xlsx,.xls,.csv"
                showUploadList={false}
                beforeUpload={handleImportExcel}
              >
                <Button icon={<UploadOutlined />}>导入Excel</Button>
              </Upload>
            )}
            {exportable && (
              <Button icon={<DownloadOutlined />} onClick={handleExportCSV}>
                导出CSV
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      {/* Table with Drag & Drop */}
      {draggable ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={data.map((item) => item[rowKey])}
            strategy={verticalListSortingStrategy}
          >
            <Table
              rowKey={rowKey}
              columns={tableColumns}
              dataSource={data}
              loading={loading}
              components={components}
              rowSelection={{
                selectedRowKeys,
                onChange: setSelectedRowKeys,
              }}
              expandable={
                willExpand
                  ? {
                      expandedRowRender: effectiveExpandedRowRender,
                      expandedRowKeys,
                      onExpand: (expanded, record) => {
                        const id = record[rowKey];
                        if (expanded) {
                          setExpandedRowKeys((prev) => [...prev, id]);
                        } else {
                          setExpandedRowKeys((prev) =>
                            prev.filter((k) => k !== id)
                          );
                        }
                      },
                    }
                  : undefined
              }
              pagination={{
                current: pagination.current,
                pageSize: pagination.pageSize,
                total: pagination.total,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
                onChange: (page, pageSize) => fetchData(page, pageSize, sortField, sortOrder),
              }}
              onChange={handleTableChange}
              scroll={{ x: 'max-content' }}
              size="middle"
            />
          </SortableContext>
          <DragOverlay>
            {activeId ? (
              <div
                style={{
                  padding: '8px 16px',
                  background: '#fff',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                  borderRadius: 4,
                }}
              >
                <HolderOutlined style={{ marginRight: 8, color: '#999' }} />
                {data.find((d) => d[rowKey] === activeId)?.[
                  columns[0]?.dataIndex as string
                ] || ''}
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      ) : (
        <Table
          rowKey={rowKey}
          columns={tableColumns}
          dataSource={data}
          loading={loading}
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys,
          }}
          expandable={
            willExpand
              ? {
                  expandedRowRender: effectiveExpandedRowRender,
                  expandedRowKeys,
                  onExpand: (expanded, record) => {
                    const id = record[rowKey];
                    if (expanded) {
                      setExpandedRowKeys((prev) => [...prev, id]);
                    } else {
                      setExpandedRowKeys((prev) =>
                        prev.filter((k) => k !== id)
                      );
                    }
                  },
                }
              : undefined
          }
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => fetchData(page, pageSize, sortField, sortOrder),
          }}
          onChange={handleTableChange}
          scroll={{ x: 'max-content' }}
          size="middle"
        />
      )}

      {/* Modal for Add / Edit */}
      <Modal
        title={editingRecord ? '编辑' : '新增'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        destroyOnClose
        width={640}
      >
        <Form form={form} layout="vertical">
          {renderFormItems()}
        </Form>
      </Modal>

      {/* Detail Drawer — combines record info + sub-tables */}
      {detailRender && detailRecord && (
        <Drawer
          title={`${title} - 详情`}
          open={!!detailRecord}
          onClose={() => setDetailRecord(null)}
          width={960}
          styles={{ body: { padding: 16 } }}
        >
          {/* Record info */}
          {detailRender(detailRecord)}
          {/* Sub-tables (expandedRowRender content) */}
          <div style={{ marginTop: 24 }}>
            {customExpandedRowRender
              ? customExpandedRowRender(detailRecord)
              : defaultExpandedRowRender(detailRecord)}
          </div>
        </Drawer>
      )}
    </Card>
  );
};

export default CrudTable;