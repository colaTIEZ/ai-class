import { describe, expect, it } from 'vitest'
import { masteryBandColor, masteryPercent } from './mastery'

describe('mastery helpers', () => {
  it('maps mastery score to color bands', () => {
    expect(masteryBandColor(undefined)).toBe('#4F46E5')
    expect(masteryBandColor(-0.5)).toBe('#4F46E5')
    expect(masteryBandColor(0.2)).toBe('#DC2626')
    expect(masteryBandColor(0.5)).toBe('#D97706')
    expect(masteryBandColor(0.9)).toBe('#16A34A')
  })

  it('converts mastery to integer percentage', () => {
    expect(masteryPercent(undefined)).toBe(0)
    expect(masteryPercent(0)).toBe(0)
    expect(masteryPercent(2 / 3)).toBe(67)
    expect(masteryPercent(1)).toBe(100)
  })
})
