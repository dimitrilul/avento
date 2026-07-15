export function dateInput(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function currentWeekRange(today = new Date()) {
  const to = new Date(today)
  to.setHours(12, 0, 0, 0)
  const from = new Date(to)
  from.setDate(from.getDate() - ((from.getDay() + 6) % 7))
  return { from: dateInput(from), to: dateInput(to) }
}
