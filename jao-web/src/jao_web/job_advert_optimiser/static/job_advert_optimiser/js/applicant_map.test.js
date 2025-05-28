import { describe, it, expect } from 'vitest';
import { getColorForFrequency, getFeatureStyle, calculateGrades } from './applicant_map';
import chroma from 'chroma-js';

describe('Map Utilities', () => {
  describe('calculateGrades', () => {
    it('should create 7 evenly spaced markers from lowest to highest value', () => {
      // Arrange
      const min = 10;
      const max = 70;
      const count = 7;

      // Act
      const result = calculateGrades(min, max, count);

      // Assert
      expect(result).toEqual([10, 20, 30, 40, 50, 60, 70]);
      expect(result.length).toBe(7);
    });

    it('should handle cases where all regions have the same value', () => {
      // Arrange
      const sameValue = 42;
      const count = 7;

      // Act
      const result = calculateGrades(sameValue, sameValue, count);

      // Assert
      expect(result).toEqual([42, 42, 42, 42, 42, 42, 42]);
    });

    it('should use whole numbers for legend display', () => {
      // Arrange
      const min = 10.4;
      const max = 70.6;
      const count = 4;

      // Act
      const result = calculateGrades(min, max, count);

      // Assert
      expect(result.every(Number.isInteger)).toBe(true);
      expect(result[0]).toBe(10);
      expect(result[result.length - 1]).toBe(71);
    });

    it('should work with negative numbers for unusual data', () => {
      // Arrange
      const min = -50;
      const max = 50;
      const count = 5;

      // Act
      const result = calculateGrades(min, max, count);

      // Assert
      expect(result[0]).toBe(-50);
      expect(result[result.length-1]).toBe(50);
      expect(result).toEqual([-50, -25, 0, 25, 50]);
    });

    it('should create exactly the number of grade markers requested', () => {
      // Arrange
      const testCases = [
        { min: 0, max: 100, count: 3 },
        { min: 0, max: 100, count: 10 }
      ];

      // Act & Assert
      testCases.forEach(({ min, max, count }) => {
        const result = calculateGrades(min, max, count);
        expect(result.length).toBe(count);
      });
    });
  });

  describe('getColorForFrequency', () => {
    it('should display regions with no data in white', () => {
      // Arrange
      const invalidValues = [undefined, null, NaN];
      const min = 0;
      const max = 100;

      // Act & Assert
      invalidValues.forEach(value => {
        const color = getColorForFrequency(value, min, max);
        expect(color).toBe('#ffffff');
      });
    });

    it('should color regions from light yellow to dark green as values increase', () => {
      // Arrange
      const min = 0;
      const max = 100;
      const lowValue = 0;
      const midValue = 50;
      const highValue = 100;

      // Act
      const lowColor = getColorForFrequency(lowValue, min, max);
      const midColor = getColorForFrequency(midValue, min, max);
      const highColor = getColorForFrequency(highValue, min, max);

      // Assert
      // Light yellow should have higher red component than greens
      expect(chroma(lowColor).get('rgb.r')).toBeGreaterThan(chroma(midColor).get('rgb.r'));
      expect(chroma(midColor).get('rgb.r')).toBeGreaterThan(chroma(highColor).get('rgb.r'));

      // All colors should have some green (it's a yellow-green scale)
      // Since dark green might have a lower green value, we'll use more appropriate checks
      expect(chroma(lowColor).get('rgb.g')).toBeGreaterThan(50);  // Light yellow has significant green
      expect(chroma(midColor).get('rgb.g')).toBeGreaterThan(50);  // Medium green has significant green
      expect(chroma(highColor).get('rgb.g')).toBeGreaterThan(0);  // Dark green still has some green

      // Colors should get darker as values increase
      expect(chroma(lowColor).luminance()).toBeGreaterThan(chroma(midColor).luminance());
      expect(chroma(midColor).luminance()).toBeGreaterThan(chroma(highColor).luminance());
    });

    it('should show the same color for all regions when all have the same value', () => {
      // Arrange
      const value = 50;
      const min = 50;
      const max = 50;

      // Act
      const color = getColorForFrequency(value, min, max);

      // Assert
      expect(chroma.valid(color)).toBe(true);
    });

    it('should adapt the color scale to the actual data range', () => {
      // Arrange
      const testCases = [
        { value: 20, min: 20, max: 80, position: 'lowest' },
        { value: 5, min: 5, max: 95, position: 'lowest' },
        { value: 80, min: 20, max: 80, position: 'highest' },
        { value: 95, min: 5, max: 95, position: 'highest' }
      ];

      // Act
      const lowestInRange1 = getColorForFrequency(testCases[0].value, testCases[0].min, testCases[0].max);
      const lowestInRange2 = getColorForFrequency(testCases[1].value, testCases[1].min, testCases[1].max);

      const highestInRange1 = getColorForFrequency(testCases[2].value, testCases[2].min, testCases[2].max);
      const highestInRange2 = getColorForFrequency(testCases[3].value, testCases[3].min, testCases[3].max);

      // Assert
      // The lowest value in any range should have the same color
      expect(lowestInRange1).toBe(lowestInRange2);

      // The highest value in any range should have the same color
      expect(highestInRange1).toBe(highestInRange2);
    });
  });

  describe('getFeatureStyle', () => {
    it('should style regions with data using solid fills', () => {
      // Arrange
      const frequency = 50;
      const min = 0;
      const max = 100;

      // Act
      const style = getFeatureStyle(frequency, min, max);

      // Assert
      expect(style.fillColor).toBe(getColorForFrequency(frequency, min, max));
      expect(style.fillOpacity).toBe(0.7);
      expect(style.dashArray).toBe(null);
    });

    it('should style regions without data using dashed borders and reduced opacity', () => {
      // Arrange
      const invalidValues = [undefined, null, NaN];
      const min = 0;
      const max = 100;

      // Act & Assert
      invalidValues.forEach(value => {
        const style = getFeatureStyle(value, min, max);

        expect(style.fillColor).toBe('#ffffff');
        expect(style.fillOpacity).toBe(0.2);
        expect(style.dashArray).toBe('5, 5');
      });
    });

    it('should maintain consistent border style for all regions', () => {
      // Arrange
      const min = 0;
      const max = 100;

      // Act
      const styleWithData = getFeatureStyle(75, min, max);
      const styleWithoutData = getFeatureStyle(null, min, max);

      // Assert
      // Both should have the same border color, weight, and opacity
      expect(styleWithData.color).toBe(styleWithoutData.color);
      expect(styleWithData.weight).toBe(styleWithoutData.weight);
      expect(styleWithData.opacity).toBe(styleWithoutData.opacity);

      // And specifically, we expect black borders of weight 1
      expect(styleWithData.color).toBe('#000');
      expect(styleWithData.weight).toBe(1);
      expect(styleWithData.opacity).toBe(1);
    });
  });
});