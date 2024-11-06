/**
 * SPDX-FileCopyrightText: 2023 Steven Hartley
 *
 * See the NOTICE file(s) distributed with this work for additional
 * information regarding copyright ownership.
 *
 * This program and the accompanying materials are made available under the
 * terms of the Apache License Version 2.0 which is available at
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package com.example.cottage2.data;

import java.util.Arrays;
import java.util.Optional;

public enum Temperatures {
    GEO_IN(0, "GEO In"),
    GEO_OUT(1, "GEO Out"),
    HEATING(2, "Heating"),
    OUTSIDE(3, "Outside"),
    ELECTRICAL(4, "Electric"),
    RETURN(5, "Return");

    private final Integer value;
    private final String name;
    private Temperatures(Integer value, String name) {
        this.name = name;
        this.value = value;
    }

    public Integer getValue() {
        return this.value;
    }
    public String getName() {
        return this.name;
    }

    public static Optional<Temperatures> from(Integer value) {
        return Arrays.stream(Temperatures.values())
                .filter(p -> p.getValue().equals(value))
                .findAny();
    }
}
