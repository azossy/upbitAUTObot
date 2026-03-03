import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../../theme/app_theme.dart';

/// 차트 표시 형태: 막대 / 라인 / 영역
enum PnlChartType { bar, line, area }

/// 일별 수익 시계열 차트 (백엔드 pnl-history API 연동). 3가지 형태 전환 가능.
class PnlHistoryChart extends StatefulWidget {
  final List<Map<String, dynamic>> data;

  const PnlHistoryChart({super.key, required this.data});

  @override
  State<PnlHistoryChart> createState() => _PnlHistoryChartState();
}

class _PnlHistoryChartState extends State<PnlHistoryChart> {
  PnlChartType _chartType = PnlChartType.bar;

  double _valueAt(int i) {
    if (i < 0 || i >= widget.data.length) return 0;
    final e = widget.data[i];
    return (e['pnl_krw'] as num?)?.toDouble() ?? (e['pnl'] as num?)?.toDouble() ?? 0.0;
  }

  String _dateAt(int i) {
    if (i < 0 || i >= widget.data.length) return '';
    return widget.data[i]['date'] as String? ?? '';
  }

  @override
  Widget build(BuildContext context) {
    if (widget.data.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 20, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(context, showSwitcher: false),
              const SizedBox(height: 24),
              Center(
                child: Text(
                  '거래 내역이 없습니다',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                      ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      );
    }

    final theme = Theme.of(context);
    final positiveColor = AppTheme.primary;
    final negativeColor = Colors.red.shade400;
    final labelColor = theme.colorScheme.onSurface.withOpacity(0.7);

    double maxY = 1;
    double minY = -1;
    for (final e in widget.data) {
      final v = _valueAt(widget.data.indexOf(e));
      if (v > maxY) maxY = v;
      if (v < minY) minY = v;
    }
    if (maxY <= minY) {
      maxY = minY + 1;
    }
    final range = (maxY - minY).clamp(0.1, double.infinity);
    final paddingY = range * 0.1;

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(context, showSwitcher: true),
            const SizedBox(height: 16),
            SizedBox(
              height: 180,
              child: _chartType == PnlChartType.bar
                  ? _buildBarChart(theme, labelColor, positiveColor, negativeColor, maxY, minY, range, paddingY)
                  : _buildLineOrAreaChart(theme, labelColor, positiveColor, maxY, minY, paddingY),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, {required bool showSwitcher}) {
    final theme = Theme.of(context);
    final labelColor = theme.colorScheme.onSurface.withOpacity(0.7);
    return Row(
      children: [
        Expanded(
          child: Text(
            '일별 수익 추이',
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: labelColor,
            ),
          ),
        ),
        if (showSwitcher) ...[
          _chartIconButton(PnlChartType.bar, Icons.bar_chart, '막대'),
          const SizedBox(width: 4),
          _chartIconButton(PnlChartType.line, Icons.show_chart, '라인'),
          const SizedBox(width: 4),
          _chartIconButton(PnlChartType.area, Icons.area_chart, '영역'),
        ],
      ],
    );
  }

  Widget _chartIconButton(PnlChartType type, IconData icon, String tooltip) {
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
    double range,
    double paddingY,
  ) {
    final barGroups = widget.data.asMap().entries.map((entry) {
      final i = entry.key;
      final v = _valueAt(i);
      final isPositive = v >= 0;
      return BarChartGroupData(
        x: i,
        barRods: [
          BarChartRodData(
            fromY: 0,
            toY: v,
            color: isPositive ? positiveColor : negativeColor,
            width: 6,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(2)),
          ),
        ],
        showingTooltipIndicators: [0],
      );
    }).toList();

    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        maxY: maxY + paddingY,
        minY: minY - paddingY,
        barTouchData: BarTouchData(
          enabled: true,
          touchTooltipData: BarTouchTooltipData(
            getTooltipColor: (_) => theme.cardTheme.color ?? theme.colorScheme.surface,
            tooltipRoundedRadius: 8,
            getTooltipItem: (group, groupIndex, rod, rodIndex) {
              if (groupIndex >= widget.data.length) return null;
              final pnlKrw = _valueAt(groupIndex);
              final label = pnlKrw >= 0 ? '+${pnlKrw.toStringAsFixed(0)}원' : '${pnlKrw.toStringAsFixed(0)}원';
              return BarTooltipItem(
                '${_dateAt(groupIndex)}\n$label',
                TextStyle(
                  color: theme.colorScheme.onSurface,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              );
            },
          ),
        ),
        titlesData: _titlesData(theme, labelColor, range),
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
    double paddingY,
  ) {
    final spots = <FlSpot>[];
    for (var i = 0; i < widget.data.length; i++) {
      spots.add(FlSpot(i.toDouble(), _valueAt(i)));
    }

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
        maxX: (widget.data.length - 1).clamp(0, double.infinity).toDouble(),
        minY: minY - paddingY,
        maxY: maxY + paddingY,
        lineTouchData: LineTouchData(
          enabled: true,
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (_) => theme.cardTheme.color ?? theme.colorScheme.surface,
            getTooltipItems: (touchedSpots) {
              return touchedSpots.map((s) {
                final i = s.x.toInt();
                final v = _valueAt(i);
                return LineTooltipItem(
                  '${_dateAt(i)}\n${v >= 0 ? '+' : ''}${v.toStringAsFixed(0)}원',
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
            dotData: const FlDotData(show: true, dotSize: 3.5),
            belowBarData: BarAreaData(
              show: _chartType == PnlChartType.area,
              gradient: fillGradient,
            ),
          ),
        ],
        titlesData: _titlesData(theme, labelColor, (maxY - minY).clamp(0.1, double.infinity)),
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

  FlTitlesData _titlesData(ThemeData theme, Color labelColor, double range) {
    return FlTitlesData(
      show: true,
      bottomTitles: AxisTitles(
        sideTitles: SideTitles(
          showTitles: true,
          getTitlesWidget: (value, meta) {
            final i = value.toInt();
            if (i >= 0 && i < widget.data.length) {
              final date = _dateAt(i);
              final short = date.length >= 10 ? date.substring(5, 10) : date;
              if (widget.data.length <= 14 || i % (widget.data.length ~/ 7).clamp(1, 31) == 0) {
                return Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    short,
                    style: theme.textTheme.bodySmall?.copyWith(color: labelColor, fontSize: 9),
                  ),
                );
              }
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
          reservedSize: 40,
          getTitlesWidget: (value, meta) {
            if (value.toInt() == value && value.abs() < 1e10) {
              return Text(
                '${value.toInt()}',
                style: theme.textTheme.bodySmall?.copyWith(color: labelColor, fontSize: 10),
              );
            }
            return Text(
              value.toStringAsFixed(0),
              style: theme.textTheme.bodySmall?.copyWith(color: labelColor, fontSize: 9),
            );
          },
          interval: range / 4,
        ),
      ),
      topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
    );
  }
}
