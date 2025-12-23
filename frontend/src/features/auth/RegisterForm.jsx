import React from 'react';
import { useForm } from 'react-hook-form';
import { Lock, AlertCircle } from 'lucide-react';
import PhoneInput from './PhoneInput';
import { isValidPhoneNumber } from 'libphonenumber-js';

function RegisterForm({ onSubmit, loading, error }) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm({
    mode: 'onChange',
    defaultValues: {
      phone_number: '',
      password: '',
      confirm_password: '',
    },
  });

  const phoneValue = watch('phone_number');
  const password = watch('password');

  const handlePhoneChange = (value) => {
    setValue('phone_number', value, { shouldValidate: true });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Phone Number Field */}
            <input
        type="hidden"
        {...register("phone_number", {
          required: "Phone number is required",
          validate: (value) => {
            if (!value || value === "+") return "Phone number is required";
            // التحقق من صحة الرقم باستخدام المكتبة
            return (
              isValidPhoneNumber(value) ||
              "Invalid phone number for this country"
            );
          },
        })}
      />

      <PhoneInput
        value={phoneValue}
        onChange={(val) => {
          // إضافة الـ + دايماً عشان الباك إند
          const formatted = val.startsWith("+") ? val : `+${val}`;
          setValue("phone_number", formatted, { shouldValidate: true });
        }}
        error={errors.phone_number?.message}
        disabled={loading}
      />

      {/* Password Field */}
      <div className="space-y-1">
        <label className="text-[10px] font-black uppercase text-main-green ml-1">
          Password
        </label>
        <div className="relative">
          <Lock
            className="absolute left-4 top-1/2 -translate-y-1/2 text-dark/30"
            size={18}
          />
          <input
            type="password"
            {...register('password', {
              required: 'Password is required',
              minLength: {
                value: 8,
                message: 'Password must be at least 8 characters',
              },
              maxLength: {
                value: 20,
                message: 'Password must be maximum 20 characters',
              },
              validate: {
                hasNumber: (value) =>
                  /\d/.test(value) || 'Password must contain at least one number',
                hasUpperCase: (value) =>
                  /[A-Z]/.test(value) ||
                  'Password must contain at least one uppercase letter',
              },
            })}
            className={`w-full bg-gray-50 border-2 ${
              errors.password ? 'border-red-500' : 'border-dark/10'
            } rounded-2xl py-4 pl-12 pr-4 font-bold focus:border-lime-yellow focus:ring-4 focus:ring-lime-yellow/20 outline-none transition-all`}
            placeholder="••••••••"
            disabled={loading}
          />
        </div>
        {errors.password && (
          <div className="flex items-center gap-2 text-red-500 text-xs mt-1 ml-1">
            <AlertCircle size={12} />
            <span>{errors.password.message}</span>
          </div>
        )}
        <p className="text-xs text-gray-500 ml-1">
          8-20 characters, 1 number, 1 uppercase letter
        </p>
      </div>

      {/* Confirm Password Field */}
      <div className="space-y-1">
        <label className="text-[10px] font-black uppercase text-main-green ml-1">
          Confirm Password
        </label>
        <div className="relative">
          <Lock
            className="absolute left-4 top-1/2 -translate-y-1/2 text-dark/30"
            size={18}
          />
          <input
            type="password"
            {...register('confirm_password', {
              required: 'Please confirm your password',
              validate: (value) => value === password || 'Passwords do not match',
            })}
            className={`w-full bg-gray-50 border-2 ${
              errors.confirm_password ? 'border-red-500' : 'border-dark/10'
            } rounded-2xl py-4 pl-12 pr-4 font-bold focus:border-lime-yellow focus:ring-4 focus:ring-lime-yellow/20 outline-none transition-all`}
            placeholder="••••••••"
            disabled={loading}
          />
        </div>
        {errors.confirm_password && (
          <div className="flex items-center gap-2 text-red-500 text-xs mt-1 ml-1">
            <AlertCircle size={12} />
            <span>{errors.confirm_password.message}</span>
          </div>
        )}
      </div>

      {/* Server Error */}
      {error && (
        <div className="flex items-center gap-2 text-red-500 text-sm p-3 bg-red-50 rounded-xl">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-dark hover:bg-main-green disabled:bg-gray-400 disabled:cursor-not-allowed text-white py-5 rounded-2xl font-black text-sm uppercase tracking-widest flex items-center justify-center gap-3 transition-all mt-6 shadow-xl shadow-gray-200"
      >
        {loading ? (
          <>
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            <span>Processing...</span>
          </>
        ) : (
          <span>Create Account</span>
        )}
      </button>
    </form>
  );
}

export default RegisterForm;