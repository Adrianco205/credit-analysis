import React from 'react';
import { clsx } from 'clsx';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'default' | 'bordered' | 'elevated' | 'soft';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ children, className, variant = 'elevated', ...props }, ref) => {
    const variants = {
      default: 'bg-white',
      bordered: 'bg-white border border-gray-200 hover:border-verde-hoja/50 transition-colors',
      elevated: 'bg-white shadow-eco-lg shadow-verde-bosque/20',
      soft: 'bg-verde-suave border border-verde-hoja/30',
    };

    return (
      <div
        ref={ref}
        className={clsx(
          'rounded-2xl p-8 transition-all duration-200',
          variants[variant],
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  children,
  className,
  ...props
}) => {
  return (
    <div className={clsx('mb-6', className)} {...props}>
      {children}
    </div>
  );
};

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
  as?: 'h1' | 'h2' | 'h3' | 'h4';
}

export const CardTitle: React.FC<CardTitleProps> = ({
  children,
  className,
  as: Component = 'h2',
  ...props
}) => {
  return (
    <Component
      className={clsx(
        'text-2xl font-bold text-gray-900 tracking-tight',
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
};

export interface CardDescriptionProps
  extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

export const CardDescription: React.FC<CardDescriptionProps> = ({
  children,
  className,
  ...props
}) => {
  return (
    <p
      className={clsx('mt-2 text-sm text-gray-600', className)}
      {...props}
    >
      {children}
    </p>
  );
};

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const CardContent: React.FC<CardContentProps> = ({
  children,
  className,
  ...props
}) => {
  return (
    <div className={clsx('space-y-4', className)} {...props}>
      {children}
    </div>
  );
};
