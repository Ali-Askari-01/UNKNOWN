import { redirect } from 'next/navigation'

export default function LegacyAdminQuizRedirect() {
  redirect('/admin/durable-quiz')
}
