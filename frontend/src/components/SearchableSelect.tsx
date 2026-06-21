import React, { useState, useEffect, useRef } from 'react';
import { Select, Input, Button, Divider, Spin } from 'antd';
import { EditOutlined, SearchOutlined } from '@ant-design/icons';
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
  /** 额外显示字段，如 'contract_no'，显示为 "name (contract_no)" */
  extraLabelKey?: string;
  /** 是否允许清除 */
  allowClear?: boolean;
  /** 是否允许手动输入（默认 true，false 时只允许从列表选择） */
  allowManual?: boolean;
  /** 表单 value */
  value?: any;
  /** 值变化回调 */
  onChange?: (value: any) => void;
  /** 模式：'default' | 'multiple' */
  mode?: 'default' | 'multiple';
}

const SearchableSelect: React.FC<SearchableSelectProps> = ({
  endpoint,
  placeholder = '请选择',
  labelKey = 'name',
  valueKey = 'id',
  extraLabelKey,
  allowClear = true,
  allowManual = true,
  value,
  onChange,
  mode,
}) => {
  const [options, setOptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [isManual, setIsManual] = useState(false);
  const [manualText, setManualText] = useState('');
  const timerRef = useRef<any>(null);
  const initialized = useRef(false);

  // 初始加载前 100 条
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    setLoading(true);
    api.get(endpoint, { params: { all: true } })
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
        setLoading(true);
        api.get(endpoint, { params: { page_size: 100 } })
          .then((res: any) => setOptions(res.items ?? []))
          .catch(() => {})
          .finally(() => setLoading(false));
        return;
      }
      setLoading(true);
      const params: any = { all: true, search: val };
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

  // 切换到手动输入模式
  const switchToManual = () => {
    setIsManual(true);
    setManualText(typeof value === 'string' ? value : '');
  };

  // 手动输入变化
  const handleManualChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setManualText(e.target.value);
    onChange?.(e.target.value);
  };

  // 如果 value 是字符串且不在选项列表中，自动切换到手动模式
  useEffect(() => {
    if (!allowManual) return;
    if (value && typeof value === 'string' && options.length > 0) {
      const found = options.some(o => String(o[valueKey]) === String(value));
      if (!found) {
        setIsManual(true);
        setManualText(value);
      }
    }
  }, [value, options, valueKey, allowManual]);

  // 手动输入模式
  if (isManual && allowManual) {
    return (
      <Input
        value={manualText}
        onChange={handleManualChange}
        placeholder={placeholder}
        suffix={
          <Button
            type="link"
            size="small"
            icon={<SearchOutlined />}
            onClick={() => setIsManual(false)}
            style={{ fontSize: 12 }}
          >
            选择
          </Button>
        }
      />
    );
  }

  return (
    <Select
      showSearch
      allowClear={allowClear}
      placeholder={placeholder}
      value={value}
      onChange={(v, option) => {
        // 如果选中的是手动输入项，切换到输入模式
        if (v === '__MANUAL_INPUT__') {
          switchToManual();
          return;
        }
        onChange?.(v);
      }}
      mode={mode}
      loading={loading}
      notFoundContent={loading ? <Spin size="small" /> : '暂无数据'}
      onSearch={handleSearch}
      searchValue={searchText}
      filterOption={false}
      style={{ width: '100%' }}
      popupRender={(menu) => (
        <>
          {menu}
          {allowManual && (
            <>
              <Divider style={{ margin: '4px 0' }} />
              <div style={{ padding: '4px 8px' }}>
                <Button
                  type="link"
                  icon={<EditOutlined />}
                  onClick={switchToManual}
                  size="small"
                >
                  手动输入自定义值
                </Button>
              </div>
            </>
          )}
        </>
      )}
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
