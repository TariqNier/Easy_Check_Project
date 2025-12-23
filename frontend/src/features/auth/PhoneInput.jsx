import React from 'react';
import PhoneInput2 from 'react-phone-input-2';
import './PhoneInput.css';
import 'react-phone-input-2/lib/style.css';
import { AlertCircle } from 'lucide-react';

function PhoneInput({ value, onChange, error, disabled }) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] font-black uppercase text-main-green ml-1">
        Phone Number
      </label>
      
      <div className="phone-wrapper">
        <PhoneInput2
          country={'eg'}
          value={value}
          onChange={onChange}
          disabled={disabled}
          enableSearch={true}
          prefix="+" 
          containerClass="phone-input-container"
          inputClass={`phone-field-style ${error ? 'phone-field-error' : ''}`}
          buttonClass="phone-button-style"
          dropdownClass="phone-dropdown-style"
          placeholder="123 456 7890"
          countryCodeEditable={false}
        />
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-500 text-xs mt-1 ml-1 font-bold">
          <AlertCircle size={12} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

export default PhoneInput;