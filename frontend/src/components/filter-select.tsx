"use client";

import { useEffect, useRef, useState } from "react";

export type FilterSelectOption = string | { value: string; label: string };

type FilterSelectProps = {
  id: string;
  label: string;
  value: string;
  placeholder: string;
  placeholderValue?: string;
  options: FilterSelectOption[];
  onChange: (value: string) => void;
};

export function FilterSelect({
  id,
  label,
  value,
  placeholder,
  placeholderValue = "",
  options,
  onChange,
}: FilterSelectProps) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const listboxId = `${id}-options`;
  const labelId = `${id}-label`;
  const normalizedOptions = options.map((option) =>
    typeof option === "string" ? { value: option, label: option } : option,
  );
  const selectedLabel =
    value === placeholderValue
      ? placeholder
      : normalizedOptions.find((option) => option.value === value)?.label || placeholder;
  const allOptions = [{ value: placeholderValue, label: placeholder }, ...normalizedOptions];

  useEffect(() => {
    if (!open) return;
    const selectedIndex = Math.max(
      0,
      allOptions.findIndex((option) => option.value === value),
    );
    setActiveIndex(selectedIndex);
    requestAnimationFrame(() => optionRefs.current[selectedIndex]?.focus());
  }, [open, value]);

  useEffect(() => {
    function closeOnOutsideClick(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
    };
  }, []);

  function selectOption(option: string) {
    onChange(option);
    setOpen(false);
    requestAnimationFrame(() => triggerRef.current?.focus());
  }

  function moveActive(nextIndex: number) {
    const normalized = (nextIndex + allOptions.length) % allOptions.length;
    setActiveIndex(normalized);
    optionRefs.current[normalized]?.focus();
  }

  function handleOptionKeyDown(event: React.KeyboardEvent, index: number) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveActive(index + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveActive(index - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      moveActive(0);
    } else if (event.key === "End") {
      event.preventDefault();
      moveActive(allOptions.length - 1);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <span id={labelId} className="sr-only">
        {label}
      </span>
      <button
        id={id}
        ref={triggerRef}
        type="button"
        aria-labelledby={`${labelId} ${id}-value`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
          }
        }}
        className={`flex min-h-11 w-full items-center justify-between gap-3 rounded border bg-white px-4 text-left text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-emerald-100 ${open ? "border-emerald-700 text-[#07152d]" : "border-slate-300 text-slate-700 hover:border-slate-400"}`}
      >
        <span
          id={`${id}-value`}
          className={`min-w-0 truncate ${value ? "text-[#07152d]" : "text-slate-500"}`}
        >
          {selectedLabel}
        </span>
        <span
          className={`text-xs text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        >
          ⌄
        </span>
      </button>
      {open && (
        <div
          id={listboxId}
          role="listbox"
          aria-label={label}
          className="absolute left-0 right-0 z-30 mt-2 max-h-64 overflow-y-auto rounded border border-slate-200 bg-white p-1 shadow-[0_12px_30px_rgba(7,21,45,0.16)]"
        >
          <button
            ref={(element) => {
              optionRefs.current[0] = element;
            }}
            type="button"
            role="option"
            aria-selected={value === placeholderValue}
            onClick={() => selectOption(placeholderValue)}
            onKeyDown={(event) => handleOptionKeyDown(event, 0)}
            tabIndex={activeIndex === 0 ? 0 : -1}
            className={`flex w-full items-center justify-between rounded px-3 py-2.5 text-left text-sm transition-colors ${value === placeholderValue ? "bg-emerald-50 font-semibold text-emerald-800" : "text-slate-600 hover:bg-slate-50 hover:text-[#07152d]"}`}
          >
            {placeholder}
            {value === placeholderValue && <span aria-hidden="true">✓</span>}
          </button>
          {normalizedOptions.map((option, optionIndex) => (
            <button
              key={option.value}
              ref={(element) => {
                optionRefs.current[optionIndex + 1] = element;
              }}
              type="button"
              role="option"
              aria-selected={value === option.value}
              onClick={() => selectOption(option.value)}
              onKeyDown={(event) => handleOptionKeyDown(event, optionIndex + 1)}
              tabIndex={activeIndex === optionIndex + 1 ? 0 : -1}
              className={`flex w-full items-center justify-between rounded px-3 py-2.5 text-left text-sm transition-colors ${value === option.value ? "bg-emerald-50 font-semibold text-emerald-800" : "text-slate-700 hover:bg-slate-50 hover:text-[#07152d]"}`}
            >
              {option.label}
              {value === option.value && <span aria-hidden="true">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
