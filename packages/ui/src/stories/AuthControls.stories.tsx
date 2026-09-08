import type { Meta, StoryObj } from '@storybook/react';
import { PasswordInput } from '../PasswordInput';
import { Stepper } from '../Stepper';
const meta = {
  title: 'Forms/PasswordInput',
  component: PasswordInput,
  args: {
    id: 'story-password',
    label: 'Пароль',
    autoComplete: 'new-password',
    hint: '10–128 символов, буква и цифра.',
  },
} satisfies Meta<typeof PasswordInput>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Error: Story = { args: { error: 'Проверьте требования к паролю.' } };
export const Disabled: Story = { args: { disabled: true } };
export const LongContent: Story = {
  args: {
    label: 'Пароль для входа в личный кабинет и продолжения работы с документами',
    hint: 'Можно использовать менеджер паролей. Не сообщайте пароль другим людям.',
  },
};
export const English: Story = {
  args: {
    label: 'Password',
    showLabel: 'Show',
    hideLabel: 'Hide',
    capsLockLabel: 'Caps Lock is on',
    hint: 'Use a password manager.',
  },
};
export const Steps: Story = {
  render: () => (
    <Stepper steps={['Аккаунт', 'Согласия', 'Далее']} current={1} label="Шаги регистрации" />
  ),
};
