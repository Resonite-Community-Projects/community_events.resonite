document.addEventListener('alpine:init', () => {
    Alpine.data('metricsPage', () => ({
        summaryData: null,
        heatmapData: null,
        domainData: null,
        clientTypeData: null,
        loadingHeatmap: false,
        loadingDomains: false,
        loadingClientTypes: false,

        dailyUsersChart: null,
        versionChart: null,
        clientTypeChart: null,
        activityHeatmap: null,
        googleMap: null,
        domainCharts: [],

        async init() {
            await this.loadGoogleCharts();
            await this.loadSummary();
            this.initSummaryCharts();
            this.loadHeatmap();
            this.loadDomains();
            this.loadClientTypes();
            this.setupResizeHandlers();
        },

        loadGoogleCharts() {
            return new Promise((resolve) => {
                if (typeof google !== 'undefined' && google.visualization) {
                    resolve();
                    return;
                }
                
                google.charts.load('current', {
                    'packages': ['geochart']
                });
                
                google.charts.setOnLoadCallback(() => {
                    console.log('Google Charts loaded');
                    resolve();
                });
            });
        },

        async loadSummary() {
            const response = await fetch('/v2/admin/metrics/summary');
            this.summaryData = await response.json();
        },

        async loadHeatmap() {
            this.loadingHeatmap = true;
            const response = await fetch('/v2/admin/metrics/heatmap');
            this.heatmapData = await response.json();
            this.loadingHeatmap = false;
            setTimeout(() => {
                this.initHeatmapChart();
            }, 100);
        },

        async loadDomains() {
            this.loadingDomains = true;
            const response = await fetch('/v2/admin/metrics/domains');
            this.domainData = await response.json();
            this.loadingDomains = false;
            this.initDomainCharts();
        },

        async loadClientTypes() {
            this.loadingClientTypes = true;
            const response = await fetch('/v2/admin/metrics/client-types');
            this.clientTypeData = await response.json();
            this.loadingClientTypes = false;
            setTimeout(() => {
                this.initClientTypeChart();
            }, 100);
        },

        initSummaryCharts() {
            if (!this.summaryData) return;
            this.initDailyUsersChart();
            this.initVersionChart();
            this.initGoogleMap();
        },

        initDailyUsersChart() {
            const chartDom = document.getElementById('daily-users-chart');
            if (!chartDom) return;

            this.dailyUsersChart = echarts.init(chartDom);
            const option = {
                tooltip: {
                    trigger: 'axis',
                    formatter: '{b}: {c} users'
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: this.summaryData.daily_unique_users_labels,
                    axisLabel: {
                        rotate: 45
                    },
                    boundaryGap: false
                },
                yAxis: {
                    type: 'value',
                    name: 'Unique Users'
                },
                series: [{
                    name: 'Unique Users',
                    type: 'line',
                    data: this.summaryData.daily_unique_users_data,
                    smooth: true,
                    lineStyle: {
                        width: 3,
                        color: '#3298dc'
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(50, 152, 220, 0.5)' },
                            { offset: 1, color: 'rgba(50, 152, 220, 0.1)' }
                        ])
                    },
                    markPoint: {
                        data: [
                            { type: 'max', name: 'Max' },
                            { type: 'min', name: 'Min' }
                        ]
                    },
                    markLine: {
                        data: [{ type: 'average', name: 'Average' }]
                    }
                }]
            };
            this.dailyUsersChart.setOption(option);
        },

        initVersionChart() {
            const chartDom = document.getElementById('version-chart-container');
            if (!chartDom) return;

            this.versionChart = echarts.init(chartDom);
            const option = {
                tooltip: {
                    trigger: 'item',
                    formatter: '{b}: {c} ({d}%)'
                },
                legend: {
                    orient: 'vertical',
                    left: 'left'
                },
                series: [{
                    name: 'Version Distribution',
                    type: 'pie',
                    radius: '70%',
                    itemStyle: {
                        borderRadius: 5,
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    label: {
                        formatter: '{b}: {d}%',
                        show: true
                    },
                    data: this.summaryData.versions.map(item => ({
                        name: item.version || 'Unknown',
                        value: item.count
                    }))
                }]
            };
            this.versionChart.setOption(option);
        },

        initClientTypeChart() {
            if (!this.clientTypeData) return;

            const chartDom = document.getElementById('client-type-chart-container');
            if (!chartDom) return;

            this.clientTypeChart = echarts.init(chartDom);
            const option = {
                tooltip: {
                    trigger: 'item',
                    formatter: '{b}: {c} ({d}%)'
                },
                series: [{
                    name: 'Client Type Distribution',
                    type: 'pie',
                    radius: '70%',
                    itemStyle: {
                        borderRadius: 5,
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    label: {
                        formatter: '{b}: {d}%',
                        show: true
                    },
                    data: this.clientTypeData.map(item => ({
                        name: item.client || 'Unknown',
                        value: item.count
                    }))
                }]
            };
            this.clientTypeChart.setOption(option);
        },

        initGoogleMap() {
            if (!this.summaryData?.country_data) { return; }

            const data = google.visualization.arrayToDataTable([
                ['Country', 'Users'],
                ...this.summaryData.country_data.map(item => [item.name, item.value])
            ]);

            const options = { colorAxis: { colors: ['#e0ffff', '#006edd'] } };
            this.googleMap = new google.visualization.GeoChart(document.getElementById('regions_div'));
            this.googleMap.draw(data, options);
        },

        initHeatmapChart() {
            if (!this.heatmapData) return;

            const chartDom = document.getElementById('activity-heatmap');
            if (!chartDom) return;

            this.activityHeatmap = echarts.init(chartDom);

            const transformedData = [];
            for (let day = 0; day < 7; day++) {
                for (let hour = 0; hour < 24; hour++) {
                    transformedData.push([hour, day, this.heatmapData[day][hour]]);
                }
            }

            let minValue = Number.MAX_VALUE;
            let maxValue = 0;
            for (let day = 0; day < 7; day++) {
                for (let hour = 0; hour < 24; hour++) {
                    const value = this.heatmapData[day][hour];
                    if (value < minValue) minValue = value;
                    if (value > maxValue) maxValue = value;
                }
            }

            const days = this.summaryData.day_labels;
            const hours = this.summaryData.hour_labels;

            const option = {
                tooltip: {
                    position: 'top',
                formatter: function (params) {
                    return `${days[params.value[1]]} at ${hours[params.value[0]]}<br>` +
                           `${params.value[2]} unique users`;
                }
                },
                grid: {
                    height: '70%',
                    top: '10%'
                },
                xAxis: {
                    type: 'category',
                    data: this.summaryData.hour_labels,
                    splitArea: {
                        show: true
                    },
                    name: 'Hour of Day',
                    nameLocation: 'middle',
                    nameGap: 40,
                    axisLabel: {
                        interval: 2,
                        fontSize: 11
                    }
                },
                yAxis: {
                    type: 'category',
                    data: this.summaryData.day_labels,
                    splitArea: {
                        show: true
                    },
                    name: 'Day of Week',
                    nameLocation: 'middle',
                    nameGap: 70
                },
                visualMap: {
                    min: minValue,
                    max: maxValue,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: '0%',
                    text: ['High', 'Low'],
                    color: ['#d62728', '#2ca02c', '#98df8a', '#d9f0d3', '#f7f7f7'],
                    textStyle: {
                        color: '#333'
                    }
                },
                series: [{
                    name: 'User Activity',
                    type: 'heatmap',
                    data: transformedData,
                    label: {
                        show: true,
                        formatter: function(params) {
                            return params.value[2] > 0 ? params.value[2] : '';
                        }
                    },
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    }
                }]
            };

            this.activityHeatmap.setOption(option);

        },

        initDomainCharts() {

            // Wait for Alpine.js to render the template
            setTimeout(() => {

                Object.entries(this.domainData || {}).forEach(([domain, metrics], index) => {

                    const sanitizedDomain = domain.replace(/\./g, '-');
                    const elementId = `domain-chart-${sanitizedDomain}`;

                    const chartDom = document.getElementById(elementId);

                    if (!chartDom) { return; }

                    const chart = echarts.init(chartDom);

                    const data = metrics.counts.map(item => ({
                        name: item.endpoint,
                        value: item.count
                    }));

                    const option = {
                        tooltip: {
                            trigger: 'item',
                            formatter: '{b}: {c} ({d}%)'
                        },
                        legend: {
                            orient: 'vertical',
                            left: 'left'
                        },
                        series: [{
                            name: 'Endpoints',
                            type: 'pie',
                            radius: '70%',
                            itemStyle: {
                                borderRadius: 5,
                                borderColor: '#fff',
                                borderWidth: 2
                            },
                            label: {
                                formatter: '{b}: {d}%',
                                show: true
                            },
                            data: data
                        }]
                    };

                    chart.setOption(option);

                    this.domainCharts = this.domainCharts || [];
                    this.domainCharts.push(chart);
                });

            }, 500);
        },

        getClientTypeTotal() {
            return (this.clientTypeData || []).reduce((sum, ct) => sum + ct.count, 0);
        },

        getClientTypePercentage(clientType) {
            const total = this.getClientTypeTotal();
            return total > 0 ? Math.round((clientType.count / total) * 100) : 0;
        },

        setupResizeHandlers() {
            window.addEventListener('resize', () => {
                if (this.dailyUsersChart) this.dailyUsersChart.resize();
                if (this.versionChart) this.versionChart.resize();
                if (this.clientTypeChart) this.clientTypeChart.resize();
                if (this.activityHeatmap) this.activityHeatmap.resize();
                if (this.domainCharts) {
                    this.domainCharts.forEach(chart => chart.resize());
                }
            });
        },

    }))
});
