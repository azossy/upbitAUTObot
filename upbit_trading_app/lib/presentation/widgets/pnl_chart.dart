import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../../theme/app_theme.dart';

/// 수익률 차트 표시 형태: 막대 / 라인 / 영역
enum PnlSummaryChartType { bar, line, area }

/// 수익률 차트 (일일, 주간 %). 3가지 형태(막대/라인/영역) 전환 가능.
class PnlChart extends StatefulWidget {
  final double dailyPnl;
  final double weeklyPnl;

  const PnlChart({
    super.key,
    required this.dailyPnl,
    required this.weeklyPnl,
  });

  @override
  State<PnlChart> createState() => _PnlChartState();
}

class _PnlChartState extends State<PnlChart> {
  PnlSummaryChartType _chartType = PnlSummaryChartType.bar;

  List<({String label, double value})> get _items => [
        (label: '일일', value: widget.dailyPnl),
        (label: '주간', value: widget.weeklyPnl),
      ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    const positiveColor = AppTheme.primary;
    final negativeColor = Colors.red.shade400;
    final labelColor = theme.colorScheme.onSurface.withOpacity(0.7);

    double maxY = 10;
    double minY = -10;
    for (final s in _items) {
      if (s.value > maxY) maxY = s.value;
      if (s.value < minY) minY = s.value;
    }
    if (maxY <= minY) {
      maxY = minY + 10;
    }
    const padding = 2.0;

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '수익률 추이',
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: labelColor,
                    ),
                  ),
                ),
                _chartIconButton(PnlSummaryChartType.bar, Icons.bar_chart, '막대'),
                const SizedBox(width: 4),
                _chartIconButton(PnlSummaryChartType.line, Icons.show_chart, '라인'),
                const SizedBox(width: 4),
                _chartIconButton(PnlSummaryChartType.area, Icons.area_chart, '영역'),
              ],
            ),
            const SizedBox(height: 20),
            SizedBox(
              height: 180,
              child: _chartType == PnlSummaryChartType.bar
                  ? _buildBarChart(theme, labelColor, positiveColor, negativeColor, maxY, minY, padding)
                  : _buildLineOrAreaChart(theme, labelColor, positiveColor, maxY, minY, padding),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chartIconButton(PnlSummaryChartType type, IconData icon, String tooltip) {
    final selected = _chartType == type;
    return Tooltip(
      message: tooltip,
      child: IconButton(
        onPressed: () => setState(() => _chartType = type),
        icon: Icon(icon, size: 22),
        color: selected ? AppTheme.primary : Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
        style: IconButton.styleFrom(
          backgroundColor: selected ? AppTheme.primary.withOpacity(0.12) : null,
        ),
      ),
    );
  }

  Widget _buildBarChart(
    ThemeData theme,
    Color labelColor,
    Color positiveColor,
    Color negativeColor,
    double maxY,
    double minY,
    double padding,
  ) {
    final barGroups = _items.asMap().entries.map((e) {
      final v = e.value.value;
      final isPositive = v >= 0;
      return BarChartGroupData(
        x: e.key,
        barRods: [
          BarChartRodData(
            fromY: 0,
            toY: v,
            color: isPositive ? positiveColor : negativeColor,
            width: 28,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
          ),
        ],
        showingTooltipIndicators: [0],
      );
    }).toList();

    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        maxY: maxY + padding,
        minY: minY - padding,
        barTouchData: BarTouchData(
          enabled: true,
          touchTooltipData: BarTouchTooltipData(
            getTooltipColor: (_) => theme.cardTheme.color ?? theme.colorScheme.surface,
            tooltipRoundedRadius: 8,
            getTooltipItem: (group, groupIndex, rod, rodIndex) {
              final item = _items[group.x];
              return BarTooltipItem(
                '${item.label}\n${item.value >= 0 ? '+' : ''}${item.value.toStringAsFixed(1)}%',
                TextStyle(
                  color: theme.colorScheme.onSurface,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              );
            },
          ),
        ),
        titlesData: FlTitlesData(
          show: true,
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                if (value.toInt() >= 0 && value.toInt() < _items.length) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      _items[value.toInt()].label,
                      style: theme.textTheme.bodySmall?.copyWith(color: labelColor),
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
              reservedSize: 28,
              interval: 1,
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 36,
              getTitlesWidget: (value, meta) {
                return Text(
                  '${value.toInt()}%',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: labelColor,
                    fontSize: 10,
                  ),
                );
              },
              interval: (maxY - minY) / 4,
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (value) => FlLine(
            color: theme.dividerColor.withOpacity(0.3),
            strokeWidth: 1,
          ),
        ),
        borderData: FlBorderData(show: false),
        barGroups: barGroups,
      ),
      duration: const Duration(milliseconds: 300),
    );
  }

  Widget _buildLineOrAreaChart(
    ThemeData theme,
    Color labelColor,
    Color lineColor,
    double maxY,
    double minY,
    double padding,
  ) {
    final spots = _items.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.value)).toList();
    final fillGradient = LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: [
        lineColor.withOpacity(0.35),
        lineColor.withOpacity(0.05),
      ],
    );

    return LineChart(
      LineChartData(
        minX: 0,
        maxX: (_items.length - 1).toDouble(),
        minY: minY - padding,
        maxY: maxY + padding,
        lineTouchData: LineTouchData(
          enabled: true,
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (_) => theme.cardTheme.color ?? theme.colorScheme.surface,
            getTooltipItems: (touchedSpots) {
              return touchedSpots.map((s) {
                final i = s.x.toInt();
                final item = _items[i];
                return LineTooltipItem(
                  '${item.label}\n${item.value >= 0 ? '+' : ''}${item.value.toStringAsFixed(1)}%',
                  TextStyle(
                    color: theme.colorScheme.onSurface,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                );
              }).toList();
            },
          ),
        ),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: lineColor,
            barWidth: 2.5,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: true),
            belowBarData: BarAreaData(
              show: _chartType == PnlSummaryChartType.area,
              gradient: fillGradient,
            ),
          ),
        ],
        titlesData: FlTitlesData(
          show: true,
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                if (value.toInt() >= 0 && value.toInt() < _items.length) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      _items[value.toInt()].label,
                      style: theme.textTheme.bodySmall?.copyWith(color: labelColor),
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
              reservedSize: 28,
              interval: 1,
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 36,
              getTitlesWidget: (value, meta) {
                return Text(
                  '${value.toInt()}%',
                  style: theme.textTheme.bodySmall?.copyWith(color: labelColor, fontSize: 10),
                );
              },
              interval: (maxY - minY) / 4,
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (value) => FlLine(
            color: theme.dividerColor.withOpacity(0.3),
            strokeWidth: 1,
          ),
        ),
        borderData: FlBorderData(show: false),
      ),
      duration: const Duration(milliseconds: 300),
    );
  }
}
