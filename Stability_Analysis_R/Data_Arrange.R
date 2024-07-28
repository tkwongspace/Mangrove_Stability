# Script to read and analyse data exported from Earth Engine

# Libraries
library(car)
library(dplyr)
library(ggplot2)
library(lubridate)
library(ggpubr)

# Arrange data
# Landsat
df1 = read.csv("../data/vi_gee/Landsat/non_protected.csv") %>%
  mutate(vi = as.factor(vi),
         lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date),
         state = 'Non-Protected') %>%
  subset(target >= 0) %>%  # remove rows that disturbed by other LULC
  group_by(fileID, pointID, vi, lat, lon, date, state) %>%
  summarise(values = mean(target)) %>%
  as.data.frame() %>%
  dplyr::select(state, vi, lat, lon, date, values)
df2 = read.csv("../data/vi_gee/Landsat/protected.csv") %>%
  mutate(vi = as.factor(vi),
         lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date),
         state = 'Protected') %>%
  subset(target >= 0) %>%  # remove rows that disturbed by other LULC
  group_by(fileID, pointID, vi, lat, lon, date, state) %>%
  summarise(values = mean(target)) %>%
  as.data.frame() %>%
  dplyr::select(state, vi, lat, lon, date, values)

landsat = bind_rows(df1, df2)
rm(df1, df2); gc()

saveRDS(landsat, file = "../data/vi_gee/Landsat_vi.rds")

# MODIS
df1 = read.csv("../data/vi_gee/MODIS/protected.csv") %>%
  mutate(vi = as.factor(vi),
         lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date),
         state = 'Protected') %>%
  subset(target >= 0) %>%
  group_by(fileID, pointID, vi, lat, lon, date, state) %>%
  summarise(values = mean(target, na.rm = T)) %>%
  as.data.frame() %>%
  dplyr::select(state, vi, lat, lon, date, values)
df2 = read.csv("../data/vi_gee/MODIS/non_protected.csv") %>%
  mutate(vi = as.factor(vi),
         lat = round(lat, 6),
         lon = round(lon, 6),
         date = ymd(date),
         state = 'Non-Protected') %>%
  subset(target >= 0) %>%
  group_by(fileID, pointID, vi, lat, lon, date, state) %>%
  summarise(values = mean(target, na.rm = T)) %>%
  as.data.frame() %>%
  dplyr::select(state, vi, lat, lon, date, values)

modis = bind_rows(df1, df2)
rm(df1, df2); gc()

saveRDS(modis, file = "../data/vi_gee/MODIS_vi.rds")

#
seasons_LUT = data.frame(months = 1:12,
                         season = c(rep('Winter', 2),
                                    rep('Spring', 3),
                                    rep('Summer', 3),
                                    rep('Autumn', 3),
                                    'Winter'))

# groupping_values = function(values, number_of_groups){
#   # find boundary
#   min_value = min(values)
#   max_value = max(values)
#   # calculate the range of each group
#   group_range = (max_value - min_value) / number_of_groups
#   # assign group tag
#   tags = sapply(values, function(value) {
#     if (value != max_value) {
#       group_number = floor((value - min_value) / group_range) + 1
#     } else {
#       group_number = floor((value - min_value) / group_range)
#     }
#     return(paste0("Group_", group_number))
#   })
#   return(tags)
# }

landsat = landsat %>% mutate(months = month(date)) %>% 
  left_join(seasons_LUT, by = 'months') %>%
  mutate(state = factor(state, levels = c('Protected', 'Non-Protected')),
         vi = factor(vi, levels = c('ndvi', 'nirv'), labels = c('NDVI', 'NIRv')),
         season = factor(season, levels = c('Spring', 'Summer', 'Autumn', 'Winter')))

modis = modis %>% mutate(months = month(date)) %>% 
  left_join(seasons_LUT, by = 'months') %>%
  mutate(state = factor(state, levels = c('Protected', 'Non-Protected')),
         vi = factor(vi, levels = c('NDVI', 'EVI')),
         season = factor(season, levels = c('Spring', 'Summer', 'Autumn', 'Winter')))

# seasonal differences
ggplot(landsat, aes(x = lat, y = values, color = season, fill = season)) +
  geom_hline(yintercept = 0, linetype = 'dotted', color = 'grey90') +
  geom_smooth() +
  facet_wrap(~vi, nrow = 1, ncol = 2, scales = 'free') +
  theme_classic() +
  theme(legend.position = 'top')

ggplot(landsat %>% subset(vi == 'NIRv') %>% 
         mutate(subs = ifelse(lat <= 20, '18-20',
                              ifelse(lat <= 22, '20-22', '22-29'))),
       aes(x = months, y = values, group = subs)) +
  geom_smooth(aes(color = subs, fill = subs), alpha = 0.2) +
  scale_x_continuous(breaks = 1:12) +
  labs(title = 'Seasonal NIRv Patterns Across Latitudes',
       x = 'Month',
       y = 'NIRv',
       color = 'Latitude',
       fill = 'Latitude') +
  facet_grid(cols = vars(state)) +
  theme_classic() +
  theme(legend.position = 'top')
