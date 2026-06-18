import React, { useState, useEffect, useRef } from 'react';
import { Select, Spin } from 'antd';
import api from '../utils/api';

interface SearchableSelectProps {
  /** API 端点路径，如 '/customers/' */
  endpoint: string;
  /** 占位文本 */
  placeholder?: string;
  /** 显示字段名（默认 'name'） */
  labelKey?: string;
  /** 值字段名（默认 'id'） */
  valueKey?: string;
  /** 额外显示字段，如 'project_no'，显示为 "name (project_no)" */
  extraLabelKey?: string;
  /** 搜索字段（默认 labelKey） */
  searchField?: string;
  /** 是否允许清除 */
  allowClear?: boolean;
  /** 表单 value */
  value?: any;
  /** 值变化回调 */
  onChange?: (value: any) => void;
  /** 模式：'default' | 'multiple' */
  mode?: 'default' | 'multiple';
  /** 自定义筛选函数（默认 filterOption） */
  filterOption?: ((input: string, option: any) => boolean) | boolean;
}

const SearchableSelect: React.FC<SearchableSelectProps> = ({
  endpoint,
  placeholder = '请选择',
  labelKey = 'name',
  valueKey = 'id',
  extraLabelKey,
  searchField,
  allowClear = true,
  value,
  onChange,
  mode,
  filterOption,
}) => {
  const [options, setOptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const timerRef = useRef<any>(null);

  // 初始加载前 100 条
  useEffect(() => {
    setLoading(true);
    api.get(endpoint, { params: { page_size: 100 } })
      .then((res: any) => {
        setOptions(res.items ?? []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [endpoint]);

  // 输入搜索（防抖 300ms）
  const handleSearch = (val: string) => {
    setSearchText(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (!val) {
        // 清空搜索时恢复初始 100 条
        setLoading(true);
        api.get(endpoint, { params: { page_size: 100 } })
          .then((res: any) => setOptions(res.items ?? []))
          .catch(() => {})
          .finally(() => setLoading(false));
        return;
      }
      setLoading(true);
      const params: any = { all: true };
      params[searchField || labelKey] = val;
      api.get(endpoint, { params })
        .then((res: any) => setOptions(res.items ?? []))
        .catch(() => {})
        .finally(() => setLoading(false));
    }, 300);
  };

  const getLabel = (item: any) => {
    const label = item[labelKey] || '';
    const extra = extraLabelKey ? item[extraLabelKey] : null;
    return extra ? `${label} (${extra})` : label;
  };

  return (
    <Select
      showSearch
      allowClear={allowClear}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      mode={mode}
      loading={loading}
      notFoundContent={loading ? <Spin size="small" /> : '暂无数据'}
      onSearch={handleSearch}
      searchValue={searchText}
      filterOption={filterOption ?? false}
      style={{ width: '100%' }}
    >
      {options.map((item: any) => (
        <Select.Option key={item[valueKey]} value={item[valueKey]}>
          {getLabel(item)}
        </Select.Option>
      ))}
    </Select>
  );
};

export default SearchableSelect;
